import hashlib
import json
import re
import ssl
import subprocess
import time
from pathlib import Path
from typing import Optional

from daktari.check import Check, CheckResult
from daktari.command_utils import CommandErrorException, CommandNotFoundException, run_command
from daktari.os import OS


def command_failure_summary(error) -> str:
    if isinstance(error, CommandErrorException):
        output = f"{error.stderr}\n{error.stdout}".strip()
        for line in output.splitlines():
            cleaned_line = line.strip()
            if cleaned_line:
                return cleaned_line
    return str(error)


def command_output(result) -> str:
    return f"{result.stderr}\n{result.stdout}".strip()


def get_available_ios_simulators():
    payload = json.loads(run_command(["xcrun", "simctl", "list", "devices", "available", "--json"]).stdout)
    devices = []

    for runtime, runtime_devices in payload.get("devices", {}).items():
        for raw_device in runtime_devices:
            name = str(raw_device.get("name", ""))
            runtime_identifier = str(runtime)
            is_ios_runtime = runtime_identifier.startswith("com.apple.CoreSimulator.SimRuntime.iOS-")
            if not raw_device.get("isAvailable", True) or not is_ios_runtime:
                continue

            devices.append(
                {
                    "udid": str(raw_device.get("udid", "")),
                    "name": name,
                    "runtime": runtime,
                    "booted": str(raw_device.get("state", "")) == "Booted",
                    "dataPath": str(raw_device.get("dataPath", "")),
                }
            )

    if len(devices) == 0:
        raise CommandErrorException("No iOS simulators found", 1, "", "No available iOS simulators found")

    return sorted(devices, key=lambda device: (device["runtime"], device["name"]), reverse=True)


def get_certificate_sha256_from_pem(pem_path) -> str:
    pem_contents = Path(pem_path).read_text()
    cert_der = ssl.PEM_cert_to_DER_cert(pem_contents)
    return hashlib.sha256(cert_der).hexdigest()


def get_available_android_avds():
    avds = [line.strip() for line in run_command(["emulator", "-list-avds"]).stdout.splitlines() if line.strip()]
    if len(avds) == 0:
        raise CommandErrorException("No Android AVDs found", 1, "", "No Android AVDs found")

    return sorted(avds)


def get_booted_android_serial_for_avd(avd_name):
    devices = run_command(["adb", "devices"]).stdout.splitlines()[1:]
    for line in devices:
        parts = line.split()
        if len(parts) < 2:
            continue

        serial = parts[0]
        status = parts[1]
        if not serial.startswith("emulator-") or status != "device":
            continue

        try:
            emu_output = run_command(["adb", "-s", serial, "emu", "avd", "name"]).stdout
        except (CommandErrorException, CommandNotFoundException):
            continue

        emu_output_lines = [line.strip() for line in emu_output.replace("\r", "").splitlines() if line.strip()]
        reported_avd_name = next((line for line in emu_output_lines if line != "OK"), "")
        if reported_avd_name == avd_name:
            return serial

    return None


def wait_for_android_device_boot(serial, timeout_seconds=240):
    deadline = time.time() + timeout_seconds
    while True:
        if time.time() > deadline:
            raise CommandErrorException(
                "Timed out waiting for Android emulator to boot",
                1,
                "",
                f"Timed out waiting for Android emulator {serial} to boot",
            )

        try:
            result = run_command(["adb", "-s", serial, "shell", "getprop", "sys.boot_completed"])
            if result.stdout.strip().replace("\r", "") == "1":
                return
        except (CommandErrorException, CommandNotFoundException):
            pass

        time.sleep(2)


def get_android_system_property(serial, property_name) -> str:
    try:
        result = run_command(["adb", "-s", serial, "shell", "getprop", property_name])
        return result.stdout.strip().replace("\r", "")
    except (CommandErrorException, CommandNotFoundException):
        return ""


def get_android_bootstrap_skip_reason(serial, avd_name, adb_root_output) -> Optional[str]:
    build_type = get_android_system_property(serial, "ro.build.type")
    build_tags = get_android_system_property(serial, "ro.build.tags")
    debuggable = get_android_system_property(serial, "ro.debuggable")
    lower_root_output = adb_root_output.lower()

    if "adbd cannot run as root in production builds" in lower_root_output:
        return (
            f"{avd_name} is running a non-rootable production image "
            f"(ro.build.type={build_type or 'unknown'}, ro.build.tags={build_tags or 'unknown'}, "
            f"ro.debuggable={debuggable or 'unknown'}). Use a Google APIs or AOSP userdebug image instead."
        )

    if debuggable == "0" or build_type == "user" or build_tags == "release-keys":
        return (
            f"{avd_name} is running a non-rootable production image "
            f"(ro.build.type={build_type or 'unknown'}, ro.build.tags={build_tags or 'unknown'}, "
            f"ro.debuggable={debuggable or 'unknown'}). Use a Google APIs or AOSP userdebug image instead."
        )

    return None


def start_android_avd_for_check(avd_name, emulator_log_path="/tmp/daktari-mobile-emulator.log"):
    with Path(emulator_log_path).open("a", encoding="utf-8") as log_file:
        subprocess.Popen(["emulator", "-avd", avd_name, "-writable-system"], stdout=log_file, stderr=subprocess.STDOUT)

    deadline = time.time() + 240
    while True:
        serial = get_booted_android_serial_for_avd(avd_name)
        if serial is not None:
            wait_for_android_device_boot(serial)
            return serial

        if time.time() > deadline:
            raise CommandErrorException(
                "Timed out waiting for Android emulator to appear",
                1,
                "",
                f"Timed out waiting for emulator '{avd_name}' to appear",
            )

        time.sleep(2)


def android_hosts_mapping_present(serial, host_alias) -> bool:
    host_alias_regex = re.escape(host_alias)
    grep_pattern = f"^10\\.0\\.2\\.2[[:space:]]+{host_alias_regex}($|[[:space:]])"
    try:
        run_command(
            [
                "adb",
                "-s",
                serial,
                "shell",
                f"grep -Eq '{grep_pattern}' /system/etc/hosts",
            ]
        )
        return True
    except (CommandErrorException, CommandNotFoundException):
        return False


class MobileIosPrerequisitesReady(Check):
    name = "mobile.ios.prerequisites"
    suggestions = {OS.OS_X: """
            Common fixes:
            - Install Xcode and launch it at least once to finish setup
            - Install an iOS simulator runtime in Xcode Settings > Platforms
            - Install mkcert and run <cmd>mkcert -install</cmd>
            """}

    def check(self) -> CheckResult:
        try:
            run_command(["mkcert", "-CAROOT"])
            run_command(["xcrun", "simctl", "list", "devices", "available", "--json"])
            get_available_ios_simulators()
            return self.passed("iOS mobile bootstrap prerequisites are met")
        except (CommandErrorException, CommandNotFoundException) as error:
            failure_reason = command_failure_summary(error)
            return self.failed(f"iOS mobile bootstrap prerequisites are <not/> met: {failure_reason}")


class MobileAndroidPrerequisitesReady(Check):
    name = "mobile.android.prerequisites"
    suggestions = {OS.GENERIC: """
            Common fixes:
            - In Android Studio, open SDK Manager > SDK Tools and install Android SDK Platform-Tools (adb)
              and Android Emulator
            - Create at least one Android Virtual Device (AVD)
            - Add Android SDK paths to your shell profile PATH (for example
              .../Android/sdk/platform-tools and .../Android/sdk/emulator)
            - Install mkcert and run <cmd>mkcert -install</cmd>
            """}

    def check(self) -> CheckResult:
        try:
            run_command(["mkcert", "-CAROOT"])
            run_command(["adb", "devices"])
            get_available_android_avds()
            return self.passed("Android mobile bootstrap prerequisites are met")
        except (CommandErrorException, CommandNotFoundException) as error:
            failure_reason = command_failure_summary(error)
            return self.failed(f"Android mobile bootstrap prerequisites are <not/> met: {failure_reason}")


class MobileIosBootstrapReady(Check):
    name = "mobile.ios.bootstrapReady"
    depends_on = [MobileIosPrerequisitesReady]

    def __init__(self, bootstrap_command: str = "task mobile:bootstrap:ios"):
        self.suggestions = {OS.OS_X: f"""
            Complete iOS simulator setup:
            <cmd>{bootstrap_command}</cmd>
            """}

    def check(self) -> CheckResult:
        try:
            simulators = get_available_ios_simulators()

            root_ca_path = Path(run_command(["mkcert", "-CAROOT"]).stdout.strip()) / "rootCA.pem"
            if not root_ca_path.exists():
                return self.failed("iOS mobile bootstrap setup is not complete")

            root_ca_sha256 = get_certificate_sha256_from_pem(root_ca_path)
            missing_simulators = []

            for simulator in simulators:
                trust_store_path = (
                    Path(simulator["dataPath"]) / "private/var/protected/trustd/private/TrustStore.sqlite3"
                )
                if not trust_store_path.exists():
                    missing_simulators.append(simulator["name"])
                    continue

                trust_query = f"select count(*) from tsettings where lower(hex(sha256)) = '{root_ca_sha256}';"
                trust_query_result = run_command(["sqlite3", str(trust_store_path), trust_query]).stdout.strip()
                if not trust_query_result.isdigit() or int(trust_query_result) < 1:
                    missing_simulators.append(simulator["name"])

            if len(missing_simulators) > 0:
                missing_names = ", ".join(sorted(set(missing_simulators)))
                return self.failed(f"iOS mobile bootstrap setup is not complete: missing on {missing_names}")

            return self.passed("iOS mobile bootstrap setup is complete")
        except (CommandErrorException, CommandNotFoundException):
            return self.failed("iOS mobile bootstrap setup is <not/> complete")


class MobileAndroidBootstrapReady(Check):
    name = "mobile.android.bootstrapReady"
    depends_on = [MobileAndroidPrerequisitesReady]

    def __init__(
        self,
        local_certificate_path,
        android_certificate_path,
        host_alias,
        bootstrap_command: str = "task mobile:bootstrap:android",
        emulator_log_path: str = "/tmp/daktari-mobile-emulator.log",
    ):
        self.local_certificate_path = local_certificate_path
        self.android_certificate_path = android_certificate_path
        self.host_alias = host_alias
        self.emulator_log_path = emulator_log_path
        self.suggestions = {OS.GENERIC: f"""
            Complete Android emulator setup for all available AVDs:
            <cmd>{bootstrap_command}</cmd>
            """}

    def check(self) -> CheckResult:
        try:
            avds = get_available_android_avds()

            local_cert_path = Path(self.local_certificate_path)
            android_cert_path = Path(self.android_certificate_path)
            if not local_cert_path.exists() or not android_cert_path.exists():
                return self.failed("Android mobile bootstrap setup is not complete")

            if local_cert_path.read_bytes() != android_cert_path.read_bytes():
                return self.failed("Android mobile bootstrap setup is not complete")

            missing_avds = []
            unsupported_avds = []
            for avd_name in avds:
                serial = get_booted_android_serial_for_avd(avd_name)
                started_by_check = serial is None

                if serial is None:
                    serial = start_android_avd_for_check(avd_name, self.emulator_log_path)
                else:
                    wait_for_android_device_boot(serial)

                try:
                    adb_root_result = run_command(["adb", "-s", serial, "root"])
                    wait_for_android_device_boot(serial)

                    skip_reason = get_android_bootstrap_skip_reason(serial, avd_name, command_output(adb_root_result))
                    if skip_reason is not None:
                        unsupported_avds.append(avd_name)
                        continue

                    hosts_ok = android_hosts_mapping_present(serial, self.host_alias)
                    if not hosts_ok:
                        missing_avds.append(avd_name)
                finally:
                    if started_by_check:
                        try:
                            run_command(["adb", "-s", serial, "emu", "kill"])
                        except (CommandErrorException, CommandNotFoundException):
                            pass

            if len(unsupported_avds) == len(avds) and len(avds) > 0:
                return self.failed(
                    "Android mobile bootstrap setup is not complete: all available AVDs are using non-rootable "
                    "production images; create a Google APIs or AOSP userdebug AVD"
                )

            if len(missing_avds) > 0:
                missing_names = ", ".join(missing_avds)
                return self.failed(f"Android mobile bootstrap setup is not complete: missing on {missing_names}")

            return self.passed("Android mobile bootstrap setup is complete")
        except (CommandErrorException, CommandNotFoundException):
            return self.failed("Android mobile bootstrap setup is <not/> complete")

import json
import tempfile
import unittest
from unittest import mock

from daktari.check import CheckStatus
from daktari.checks.mobile import (
    MobileAndroidBootstrapReady,
    command_failure_summary,
    get_available_android_avds,
    get_available_ios_simulators,
)
from daktari.command_utils import CommandErrorException, SuccessfulCommandResult


class TestCommandFailureSummary(unittest.TestCase):
    def test_extracts_first_non_empty_line_from_command_error(self):
        error = CommandErrorException("failed", 1, "", "\nfirst line\nsecond line")

        self.assertEqual("first line", command_failure_summary(error))

    def test_falls_back_to_error_string(self):
        self.assertEqual("boom", command_failure_summary(Exception("boom")))


class TestMobileHelpers(unittest.TestCase):
    @mock.patch("daktari.checks.mobile.run_command")
    def test_get_available_ios_simulators_filters_non_ios_and_unavailable(self, mock_run_command):
        payload = {
            "devices": {
                "com.apple.CoreSimulator.SimRuntime.iOS-18-0": [
                    {
                        "name": "iPhone 16",
                        "udid": "ios-1",
                        "state": "Shutdown",
                        "isAvailable": True,
                        "dataPath": "/tmp/ios-1",
                    },
                    {
                        "name": "Unavailable",
                        "udid": "ios-2",
                        "state": "Shutdown",
                        "isAvailable": False,
                        "dataPath": "/tmp/ios-2",
                    },
                ],
                "com.apple.CoreSimulator.SimRuntime.tvOS-18-0": [
                    {
                        "name": "Apple TV",
                        "udid": "tvos-1",
                        "state": "Shutdown",
                        "isAvailable": True,
                        "dataPath": "/tmp/tvos-1",
                    }
                ],
            }
        }
        mock_run_command.return_value.stdout = json.dumps(payload)

        simulators = get_available_ios_simulators()

        self.assertEqual(1, len(simulators))
        self.assertEqual("iPhone 16", simulators[0]["name"])

    @mock.patch("daktari.checks.mobile.run_command")
    def test_get_available_android_avds_returns_sorted_list(self, mock_run_command):
        mock_run_command.return_value.stdout = "Pixel_8\n\nPixel_7\n"

        self.assertEqual(["Pixel_7", "Pixel_8"], get_available_android_avds())

    @mock.patch("daktari.checks.mobile.run_command")
    def test_get_available_android_avds_raises_when_none_available(self, mock_run_command):
        mock_run_command.return_value.stdout = "\n"

        with self.assertRaisesRegex(CommandErrorException, "No Android AVDs found"):
            get_available_android_avds()


class TestMobileAndroidBootstrapReady(unittest.TestCase):
    def test_fails_when_all_available_avds_are_non_rootable(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            local_certificate_path = f"{temp_dir}/local.pem"
            android_certificate_path = f"{temp_dir}/android.pem"
            with open(local_certificate_path, "wb") as local_cert_file:
                local_cert_file.write(b"same")
            with open(android_certificate_path, "wb") as android_cert_file:
                android_cert_file.write(b"same")

            check = MobileAndroidBootstrapReady(
                local_certificate_path,
                android_certificate_path,
                "local.example.test",
            )

            with (
                mock.patch(
                    "daktari.checks.mobile.get_available_android_avds",
                    return_value=["Medium_Phone_API_35"],
                ),
                mock.patch(
                    "daktari.checks.mobile.get_booted_android_serial_for_avd",
                    return_value="emulator-5554",
                ),
                mock.patch(
                    "daktari.checks.mobile.run_command",
                    return_value=SuccessfulCommandResult(
                        stdout="adbd cannot run as root in production builds\n",
                        stderr="",
                    ),
                ),
                mock.patch("daktari.checks.mobile.wait_for_android_device_boot"),
                mock.patch(
                    "daktari.checks.mobile.get_android_bootstrap_skip_reason",
                    return_value="Medium_Phone_API_35 is running a non-rootable production image",
                ),
            ):
                result = check.check()

        self.assertEqual(CheckStatus.FAIL, result.status)
        self.assertIn("all available AVDs are using non-rootable production images", result.summary)

    def test_ignores_non_rootable_avds_when_supported_avds_are_bootstrapped(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            local_certificate_path = f"{temp_dir}/local.pem"
            android_certificate_path = f"{temp_dir}/android.pem"
            with open(local_certificate_path, "wb") as local_cert_file:
                local_cert_file.write(b"same")
            with open(android_certificate_path, "wb") as android_cert_file:
                android_cert_file.write(b"same")

            check = MobileAndroidBootstrapReady(
                local_certificate_path,
                android_certificate_path,
                "local.example.test",
            )

            with (
                mock.patch(
                    "daktari.checks.mobile.get_available_android_avds",
                    return_value=["Pixel_8_API_35", "Medium_Phone_API_35"],
                ),
                mock.patch(
                    "daktari.checks.mobile.get_booted_android_serial_for_avd",
                    return_value="emulator-5554",
                ) as mock_get_serial,
                mock.patch(
                    "daktari.checks.mobile.run_command",
                    return_value=SuccessfulCommandResult(stdout="restarting adbd as root\n", stderr=""),
                ),
                mock.patch("daktari.checks.mobile.wait_for_android_device_boot"),
                mock.patch(
                    "daktari.checks.mobile.get_android_bootstrap_skip_reason",
                    side_effect=[None, "Medium_Phone_API_35 is running a non-rootable production image"],
                ),
                mock.patch(
                    "daktari.checks.mobile.android_hosts_mapping_present",
                    return_value=True,
                ),
            ):
                result = check.check()

        self.assertEqual(CheckStatus.PASS, result.status)
        self.assertEqual(2, mock_get_serial.call_count)


if __name__ == "__main__":
    unittest.main()

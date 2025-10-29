import logging
from os.path import expanduser
from typing import Dict, Optional

from python_hosts import Hosts

from daktari.check import Check, CheckResult
from daktari.os import OS, check_env_var_exists, get_env_var_value
from daktari.version_utils import get_simple_cli_version
from daktari.command_utils import can_run_command


class WatchmanInstalled(Check):
    name = "watchman.installed"

    suggestions = {
        OS.OS_X: "<cmd>brew install watchman</cmd>",
        OS.GENERIC: "Install watchman: https://facebook.github.io/watchman/docs/install.html#buildinstall",
    }

    def check(self) -> CheckResult:
        return self.verify_install("watchman")


class MkcertInstalled(Check):
    name = "mkcert.installed"

    suggestions = {
        OS.OS_X: """
            Install mkcert:
            <cmd>brew install mkcert</cmd>
            Install the local CA in the system trust store:
            <cmd>mkcert -install</cmd>
            """,
        OS.GENERIC: """
            Install mkcert: https://mkcert.dev/#installation
            Install the local CA in the system trust store:
            <cmd>mkcert -install</cmd>
            """,
    }

    def check(self) -> CheckResult:
        return self.verify_install("mkcert")


class KtlintInstalled(Check):
    name = "ktlint.installed"

    suggestions = {
        OS.OS_X: "<cmd>brew install ktlint</cmd>",
        OS.GENERIC: "Install ktlint: https://github.com/pinterest/ktlint#installation",
    }

    def __init__(self, required_version: Optional[str] = None, recommended_version: Optional[str] = None):
        self.required_version = required_version
        self.recommended_version = recommended_version

    def check(self) -> CheckResult:
        installed_version = get_simple_cli_version("ktlint")
        return self.validate_semver_expression(
            "ktlint", installed_version, self.required_version, self.recommended_version
        )


class CmakeInstalled(Check):
    name = "cmake.installed"

    suggestions = {
        OS.OS_X: "<cmd>brew install cmake</cmd>",
        OS.UBUNTU: "<cmd>apt-get install cmake</cmd>",
        OS.GENERIC: "Install cmake: https://cmake.org/install/",
    }

    def __init__(self, required_version: Optional[str] = None, recommended_version: Optional[str] = None):
        self.required_version = required_version
        self.recommended_version = recommended_version

    def check(self) -> CheckResult:
        installed_version = get_simple_cli_version("cmake")
        return self.validate_semver_expression(
            "cmake", installed_version, self.required_version, self.recommended_version
        )


class JqInstalled(Check):
    name = "jq.installed"

    suggestions = {
        OS.OS_X: "<cmd>brew install jq</cmd>",
        OS.UBUNTU: "<cmd>sudo apt install jq</cmd>",
        OS.GENERIC: "Install jq: https://stedolan.github.io/jq/download/",
    }

    def check(self) -> CheckResult:
        return self.verify_install("jq")


class FlywayInstalled(Check):
    name = "flyway.installed"

    suggestions = {
        OS.OS_X: "<cmd>brew install flyway</cmd>",
        OS.UBUNTU: "<cmd>snap install flyway</cmd>",
        OS.GENERIC: "Install flyway: https://flywaydb.org/documentation/usage/commandline/#download-and-installation",
    }

    def check(self) -> CheckResult:
        return self.verify_install("flyway", "-v")


class ShellcheckInstalled(Check):
    name = "shellcheck.installed"

    suggestions = {
        OS.OS_X: "<cmd>brew install shellcheck</cmd>",
        OS.UBUNTU: "<cmd>sudo apt install shellcheck</cmd>",
        OS.GENERIC: "Install shellcheck: https://github.com/koalaman/shellcheck#user-content-installing",
    }

    def check(self) -> CheckResult:
        return self.verify_install("shellcheck")


class MakeInstalled(Check):
    name = "make.installed"

    suggestions = {
        OS.OS_X: "<cmd>xcode-select --install</cmd>",
        OS.UBUNTU: "<cmd>sudo apt install make</cmd>",
        OS.GENERIC: "Install make: https://www.gnu.org/software/make/",
    }

    def check(self) -> CheckResult:
        return self.verify_install("make")


class GccInstalled(Check):
    name = "gcc.installed"

    suggestions = {
        OS.OS_X: "<cmd>xcode-select --install</cmd>",
        OS.UBUNTU: "<cmd>sudo apt install gcc</cmd>",
        OS.GENERIC: "Install gcc: https://gcc.gnu.org/",
    }

    def check(self) -> CheckResult:
        return self.verify_install("gcc")


class EnvVarSet(Check):
    def __init__(self, variable_name: str, variable_value: Optional[str] = "", provision_command: str = ""):
        self.name = f"env.variableSet.{variable_name}"
        self.suggestions = {OS.GENERIC: provision_command}
        self.variable_name = variable_name
        self.variable_value = variable_value

    def check(self) -> CheckResult:
        if self.variable_value:
            return self.verify(
                get_env_var_value(self.variable_name) == self.variable_value,
                f"{self.variable_name} has <not/> got the required value of {self.variable_value}",
            )
        else:
            return self.verify(check_env_var_exists(self.variable_name), f"{self.variable_name} is <not/> set")


class ShfmtInstalled(Check):
    name = "shfmt.installed"

    suggestions = {
        OS.OS_X: "<cmd>brew install shfmt</cmd>",
        OS.UBUNTU: "<cmd>snap install shfmt</cmd>",
        OS.GENERIC: "Install shfmt: https://github.com/mvdan/sh",
    }

    def check(self) -> CheckResult:
        return self.verify_install("shfmt")


class Md5SumInstalled(Check):
    name = "md5sum.installed"

    suggestions = {OS.OS_X: "<cmd>brew install md5sha1sum</cmd>", OS.GENERIC: "Install md5sum"}

    def check(self) -> CheckResult:
        return self.verify_install("md5sum")


class HostAliasesConfigured(Check):
    name = "hostAliases.configured"

    def __init__(self, required_aliases: Dict[str, str]):
        self.required_aliases = required_aliases
        hosts_path = Hosts.determine_hosts_path()

        aliases_by_addr: Dict[str, list[str]] = {}

        for name, addr in self.required_aliases.items():
            aliases_by_addr.setdefault(addr, []).append(name)

        lines = [f"{addr} {' '.join(names)}" for addr, names in aliases_by_addr.items()]
        entries_text = "\n".join(lines)

        suggestion_text = (
            f"Add the following entries to {hosts_path}:\n\n{entries_text}\n\n"
            "Note: If you already have entries for these IP addresses, "
            "please merge these aliases onto the existing lines."
        )
        self.suggestions = {OS.GENERIC: suggestion_text}

    def check(self) -> CheckResult:
        hosts = Hosts()
        entries = [e for e in hosts.entries if e.entry_type in ("ipv4", "ipv6")]
        entries_dict = {}
        for entry in entries:
            for name in entry.names:
                entries_dict[name] = entry.address
        logging.debug(f"Hosts file entries: {entries_dict}")
        for name, address in self.required_aliases.items():
            if entries_dict.get(name) != address:
                return self.failed(f"{hosts.path} alias {name} -> {address} not present")

        return self.passed(f"{hosts.path} aliases present")


class DirectoryIsOnPath(Check):
    name = "directory.on.path"

    def __init__(self, directory: str):
        self.directory = expanduser(directory)  # $PATH won't auto-expand ~
        self.suggestions = {
            OS.GENERIC: f"""
                Append the following line to your profile (~/.bashrc or ~/.zshrc):
                export PATH="{self.directory}:$PATH
                """,
            OS.UBUNTU: f"""
                Append the following line to your profile (~/.bashrc):
                export PATH="{self.directory}:$PATH"
                For first time setup, you can run this:
                <cmd>echo 'export PATH="{self.directory}:$PATH"' >> ~/.bashrc && source ~/.bashrc</cmd>
                """,
            OS.OS_X: f"""
                Append the following line to your profile (~/.zshrc):
                export PATH="{self.directory}:$PATH"
                For first time setup, you can run this:
                <cmd>echo 'export PATH="{self.directory}:$PATH"' >> ~/.zshrc && source ~/.zshrc</cmd>
                """,
        }

    def check(self) -> CheckResult:
        path_value = get_env_var_value("PATH")
        return self.verify(path_value.__contains__(self.directory), f"{self.directory} is <not/> on the $PATH")


class DetektInstalled(Check):
    name = "detekt.installed"

    def __init__(
        self,
        required_version: Optional[str] = None,
        recommended_version: Optional[str] = None,
        install_version: Optional[str] = None,
    ):
        self.install_version = install_version
        self.required_version = required_version
        self.recommended_version = recommended_version
        self.suggestions = {
            OS.OS_X: self.get_install_cmd(),
            OS.UBUNTU: self.get_install_cmd(),
            OS.GENERIC: "Install detekt: https://detekt.dev/cli.html#install-the-cli",
        }

    def get_install_cmd(self) -> str:
        version = self.install_version or "[desired version - see https://github.com/detekt/detekt/releases]"
        url = "https://github.com/detekt/detekt/releases/download/v$DETEKT_VERSION/detekt-cli-$DETEKT_VERSION.zip"
        return f"""
            <cmd>DETEKT_VERSION={version}</cmd>
            <cmd>LOCAL_BIN=~/.local/bin</cmd>
            <cmd>TEMP_FILE=$(mktemp)</cmd>
            <cmd>mkdir -p "$LOCAL_BIN"</cmd>
            <cmd>curl -L {url} --output "$TEMP_FILE"</cmd>
            <cmd>unzip -u "$TEMP_FILE" -d "$LOCAL_BIN"</cmd>
            <cmd>rm "$TEMP_FILE"</cmd>
            <cmd>chmod +x "$LOCAL_BIN/detekt-cli-$DETEKT_VERSION/bin/detekt-cli"</cmd>
            <cmd>ln -f -s "$LOCAL_BIN/detekt-cli-$DETEKT_VERSION/bin/detekt-cli" "$LOCAL_BIN/detekt"</cmd>
            """

    def check(self) -> CheckResult:
        installed_version = get_simple_cli_version("detekt")
        return self.validate_semver_expression(
            "detekt", installed_version, self.required_version, self.recommended_version
        )


class TaskInstalled(Check):
    name = "task.installed"
    suggestions = {
        OS.OS_X: "<cmd>brew install go-task</cmd>",
        OS.GENERIC: "Install task: https://taskfile.dev/installation/",
    }

    def check(self) -> CheckResult:
        return self.verify_install("task")


class Rosetta2Installed(Check):
    name = "rosetta2.installed"
    run_on = OS.OS_X
    suggestions = {OS.OS_X: "<cmd>softwareupdate --install-rosetta</cmd>"}

    def check(self) -> CheckResult:
        return self.verify(
            can_run_command("arch -x86_64 true"), "Rosetta 2 is installed or not required", "Rosetta 2 is not installed"
        )

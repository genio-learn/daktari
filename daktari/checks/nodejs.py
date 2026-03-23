import logging
from typing import List, Optional

from semver import VersionInfo

from daktari.check import Check, CheckResult
from daktari.command_utils import get_stdout, run_command
from daktari.os import OS
from daktari.version_utils import try_parse_semver


def get_nodejs_version() -> Optional[VersionInfo]:
    version_output = get_stdout("node --version")
    version_output = None if version_output is None else version_output.lstrip("v")
    return try_parse_semver(version_output)


def run_nvm(nvm_args: List[str]):
    return run_command(["sh", "-c", '. "$NVM_DIR/nvm.sh"; nvm "$@"', "--", *nvm_args])


def can_run_nvm() -> bool:
    try:
        run_nvm(["--version"])
        return True
    except Exception:
        logging.debug("Exception running nvm", exc_info=True)
        return False


def get_nvmrc_version() -> Optional[str]:
    try:
        with open(".nvmrc", "r") as nvmrc_file:
            return nvmrc_file.readline().strip()
    except IOError:
        logging.debug("Could not read .nvmrc", exc_info=True)
        return None


class NodeJsVersion(Check):
    name = "nodejs.version"

    def __init__(self, required_version: str, recommended_version: Optional[str] = None):
        self.required_version = required_version
        self.recommended_version = recommended_version

    suggestions = {
        OS.GENERIC: "Install node.js",
    }

    def check(self) -> CheckResult:
        nodejs_version = get_nodejs_version()
        logging.info(f"node.js version: {nodejs_version}")
        return self.validate_semver_expression(
            "node.js", nodejs_version, self.required_version, self.recommended_version
        )


class NvmInstalled(Check):
    name = "nvm.installed"

    suggestions = {OS.GENERIC: "Install nvm from: https://nvm.sh"}

    def check(self) -> CheckResult:
        return self.verify(can_run_nvm(), "nvm is <not/> installed")


class NodeJsVersionMatchesNvmrc(Check):
    name = "nodejs.nvmrc.version"

    suggestions = {OS.GENERIC: """
            Run: <cmd>nvm install</cmd> (automatically picks up the right version from .nvmrc)
            Run: <cmd>nvm use</cmd>
            Run: <cmd>nvm alias default <version></cmd> to set the default node version to the newly
            installed one
            """}

    def check(self) -> CheckResult:
        nvmrc_version = get_nvmrc_version()
        if nvmrc_version is None:
            return self.failed("Missing or invalid .nvmrc file")

        active_version = get_nodejs_version()
        if active_version is None:
            return self.failed(f'node.js version "{nvmrc_version}" is not installed')

        if active_version != nvmrc_version:
            return self.failed(f'the active node.js version is {active_version}, "{nvmrc_version}" is required')

        return self.passed(f"node.js version is {active_version}")

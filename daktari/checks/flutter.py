import logging
import re
from semver import VersionInfo
from typing import Optional

from daktari.check import Check, CheckResult
from daktari.command_utils import get_stdout
from daktari.os import OS
from daktari.version_utils import try_parse_semver

flutter_version_pattern = re.compile(r"Flutter\s+([\d\.]+)")


def parse_flutter_version_output(version_output: Optional[str]) -> Optional[VersionInfo]:
    if version_output:
        match = flutter_version_pattern.search(version_output)
        if match:
            version_string = match.group(1)
            logging.debug(f"Flutter version string: {version_string}")
            return try_parse_semver(version_string)
    return None


def get_flutter_version() -> Optional[VersionInfo]:
    version_output = get_stdout("flutter --version")
    return parse_flutter_version_output(version_output)


class FlutterInstalled(Check):
    name = "flutter.installed"

    suggestions = {
        OS.GENERIC: "Install Flutter: https://flutter.dev/docs/get-started/install",
    }

    def __init__(self, required_version: Optional[str] = None, recommended_version: Optional[str] = None):
        self.required_version = required_version
        self.recommended_version = recommended_version

    def check(self) -> CheckResult:
        flutter_version = get_flutter_version()
        logging.info(f"Flutter version: {flutter_version}")
        return self.validate_semver_expression(
            "Flutter", flutter_version, self.required_version, self.recommended_version
        )

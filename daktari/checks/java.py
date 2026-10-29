import logging
import re
from typing import Optional

from semver import VersionInfo

from daktari.check import Check, CheckResult
from daktari.command_utils import get_stderr, run_command
from daktari.os import OS

java_version_pattern = re.compile('^.*version "(.*?)".*$', re.MULTILINE)
javac_version_pattern = re.compile("^javac (.*)$", re.MULTILINE)

one_dot_pattern = re.compile("^1\\.([0-9]+)")
other_pattern = re.compile("([0-9]+)")


def get_java_version() -> Optional[VersionInfo]:
    version_output = get_stderr("java -version")
    return parse_java_version_output(version_output)


def get_jdk_version() -> Optional[VersionInfo]:
    try:
        version_output = run_command("javac -version")
    except Exception:
        return None

    return parse_javac_version_output(version_output.stdout + version_output.stderr)


def parse_java_version_output(version_output: Optional[str]) -> Optional[VersionInfo]:
    if version_output:
        match = java_version_pattern.search(version_output)
        if match:
            version_string = match.group(1)
            logging.debug(f"Java version string: {version_string}")
            return parse_java_version_string(version_string)
    return None


def parse_javac_version_output(version_output: Optional[str]) -> Optional[VersionInfo]:
    if version_output:
        match = javac_version_pattern.search(version_output)
        if match:
            version_string = match.group(1)
            logging.debug(f"JDK version string: {version_string}")
            return parse_java_version_string(version_string)
    return None


def parse_java_version_string(version_string: str) -> Optional[VersionInfo]:
    try:
        return VersionInfo.parse(version_string)
    except ValueError:
        return parse_alternative_java_version_numbers(version_string)


def parse_alternative_java_version_numbers(version_string: str) -> Optional[VersionInfo]:
    one_dot_match = one_dot_pattern.search(version_string)
    if one_dot_match:
        return VersionInfo(int(one_dot_match.group(1)))
    other_pattern_match = other_pattern.search(version_string)
    if other_pattern_match:
        return VersionInfo(int(other_pattern_match.group(1)))
    return None


class JavaVersion(Check):
    name = "java.version"

    def __init__(
        self,
        required_version: Optional[str] = None,
        recommended_version: Optional[str] = None,
        java_instructions: Optional[str] = None,
    ):
        self.required_version = required_version
        self.recommended_version = recommended_version

        java_instructions = f"\n\n{java_instructions}" if java_instructions else ""
        self.suggestions = {OS.GENERIC: f"""Install Java{java_instructions}"""}

    def check(self) -> CheckResult:
        java_version = get_java_version()
        logging.info(f"Java version: {java_version}")
        return self.validate_semver_expression("Java", java_version, self.required_version, self.recommended_version)


class JdkVersion(Check):
    name = "jdk.version"

    def __init__(self, required_version: str, recommended_version: Optional[str] = None):
        self.required_version = required_version
        self.recommended_version = recommended_version

    suggestions = {
        OS.GENERIC: "Install Java JDK",
    }

    def check(self) -> CheckResult:
        jdk_version = get_jdk_version()
        logging.info(f"JDK version: {jdk_version}")
        return self.validate_semver_expression("JDK", jdk_version, self.required_version, self.recommended_version)

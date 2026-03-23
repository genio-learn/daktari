import logging
import re
from typing import Optional

from semver import VersionInfo

from daktari.command_utils import get_stdout

generic_version_pattern = re.compile("([0-9.]+)")


def get_simple_cli_version(binary_name: str) -> Optional[VersionInfo]:
    raw_version = get_stdout(f"{binary_name} --version")
    if raw_version:
        match = generic_version_pattern.search(raw_version)
        if match:
            version = try_parse_semver(match.group(1))
            logging.debug(f"{binary_name} version: {version}")
            return version
    return None


def try_parse_semver(version_str: Optional[str]) -> Optional[VersionInfo]:
    try:
        return None if version_str is None else VersionInfo.parse(_sanitise_version_string(version_str))
    except ValueError:
        return None


# Coerce version strings into a standard semver format: major.minor.patch
def _sanitise_version_string(version_str: str) -> str:
    parts = version_str.split(".")
    if len(parts) == 2:
        return version_str + ".0"
    elif len(parts) >= 4:
        return ".".join(parts[:3])
    return version_str

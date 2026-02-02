import logging
import os
from dataclasses import dataclass
from typing import List, Optional
from urllib.parse import urlparse

from daktari.check import Check, CheckResult
from daktari.command_utils import can_run_command
from daktari.file_utils import file_exists
from daktari.os import OS


@dataclass
class NpmrcScope:
    name: str
    registry: str
    requireAuthToken: bool = False


def get_npmrc_path() -> str:
    return os.path.expanduser("~/.npmrc")


def get_npmrc_contents() -> List[str]:
    npmrc_path = get_npmrc_path()
    if not file_exists(npmrc_path):
        raise Exception(f"{npmrc_path} does not exist")

    try:
        with open(npmrc_path, "r") as npmrc_file:
            return npmrc_file.readlines()
    except Exception:
        logging.error(f"Exception reading {npmrc_path}", exc_info=True)
        raise Exception("Failed to read npmrc")


def get_registry_host(registry_url: str) -> str:
    parsed = urlparse(registry_url)
    return parsed.netloc


def npmrc_contains_scope_registry(lines: List[str], scope: NpmrcScope) -> bool:
    expected_line = f"@{scope.name}:registry={scope.registry}"
    for line in lines:
        stripped = line.strip()
        if stripped == expected_line or stripped.startswith(expected_line + "\n"):
            return True
    return False


def npmrc_contains_auth_token(lines: List[str], registry_url: str) -> bool:
    host = get_registry_host(registry_url)
    auth_token_prefix = f"//{host}/:_authToken="
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(auth_token_prefix):
            token_value = stripped[len(auth_token_prefix) :]
            if token_value and token_value != "UPDATE_WITH_TOKEN":
                return True
    return False


def npmrc_scope_is_configured(lines: List[str], scope: NpmrcScope) -> bool:
    if not npmrc_contains_scope_registry(lines, scope):
        return False
    if scope.requireAuthToken and not npmrc_contains_auth_token(lines, scope.registry):
        return False
    return True


def get_npmrc_suggestion(scope: NpmrcScope) -> str:
    lines = [f"@{scope.name}:registry={scope.registry}"]
    if scope.requireAuthToken:
        host = get_registry_host(scope.registry)
        lines.append(f"//{host}/:_authToken=UPDATE_WITH_TOKEN")
    return "\n".join(lines)


def get_npmrc_token_for_registry(registry_url: str) -> Optional[str]:
    lines = get_npmrc_contents()
    host = get_registry_host(registry_url)
    auth_token_prefix = f"//{host}/:_authToken="
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(auth_token_prefix):
            return stripped[len(auth_token_prefix) :]
    return None


class NpmrcScopeConfigured(Check):
    name = "npmrc.scopeConfigured"

    def __init__(self, scope: NpmrcScope, tokenInstructions: Optional[str] = None):
        self.scope = scope
        self.npmrc_suggestion = get_npmrc_suggestion(scope)
        tokenInstructionString = f"\n\n{tokenInstructions}" if tokenInstructions else ""
        self.suggestions = {
            OS.GENERIC: f"""Add the lines below to ~/.npmrc:

{self.npmrc_suggestion}{tokenInstructionString}"""
        }

    def check(self) -> CheckResult:
        try:
            lines = get_npmrc_contents()
        except Exception as e:
            return self.failed(str(e))

        if not npmrc_scope_is_configured(lines, self.scope):
            return self.failed(f"Scope {self.scope.name} not configured in npmrc")

        return self.passed(f"Scope {self.scope.name} configured in npmrc")


class NpmrcGithubTokenValid(Check):
    name = "npmrc.githubTokenValid"
    depends_on = [NpmrcScopeConfigured]

    def __init__(self, scope_name: str, test_package: str):
        self.scope_name = scope_name
        self.test_package = test_package
        self.suggestions = {
            OS.GENERIC: "Please check the token was copied correctly from GitHub."
            " Ensure the token hasn't expired, or has been revoked."
            " Also, ensure it has the correct permissions to read packages."
        }

    def check(self) -> CheckResult:
        package_spec = f"@{self.scope_name}/{self.test_package}"
        command = f"npm view {package_spec} version"
        logging.debug(f"Checking npm registry access with: {command}")

        if can_run_command(command):
            return self.passed(f"GitHub npm token is valid (can access {package_spec})")
        else:
            return self.failed(f"GitHub npm token is not valid (cannot access {package_spec})")

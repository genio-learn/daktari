import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, Optional

import yaml
from yaml.error import YAMLError

from daktari.check import Check, CheckResult
from daktari.file_utils import file_exists
from daktari.os import OS
import requests


class YarnInstalled(Check):
    name = "yarn.installed"

    suggestions = {
        OS.OS_X: "<cmd>brew install yarn</cmd>",
        OS.GENERIC: "<cmd>npm install -g yarn</cmd>",
    }

    def check(self) -> CheckResult:
        return self.verify_install("yarn")


@dataclass
class YarnNpmScope:
    name: str
    npmPublishRegistry: Optional[str] = None
    npmRegistryServer: Optional[str] = None
    npmAlwaysAuth: Optional[bool] = None
    requireNpmAuthToken: bool = False


def get_yarnrc_path() -> str:
    return os.path.expanduser("~/.yarnrc.yml")


def get_yarnrc_suggestion(scope: YarnNpmScope) -> str:
    scope_yaml: Dict[str, Any] = {}
    if scope.npmRegistryServer is not None:
        scope_yaml["npmRegistryServer"] = scope.npmRegistryServer
    if scope.npmPublishRegistry is not None:
        scope_yaml["npmPublishRegistry"] = scope.npmPublishRegistry
    if scope.requireNpmAuthToken:
        scope_yaml["npmAuthToken"] = "UPDATE WITH GITHUB ACCESS TOKEN"
    if scope.npmAlwaysAuth is not None:
        scope_yaml["npmAlwaysAuth"] = scope.npmAlwaysAuth
    yarnrc_yaml = {"npmScopes": {scope.name: scope_yaml}}
    return yaml.dump(yarnrc_yaml)


def match_scope(template: YarnNpmScope, scope: Dict[str, Any]) -> bool:
    if template.npmPublishRegistry is not None and template.npmPublishRegistry != scope.get("npmPublishRegistry", None):
        return False
    if template.npmRegistryServer is not None and template.npmRegistryServer != scope.get("npmRegistryServer", None):
        return False
    if template.npmAlwaysAuth is not None and template.npmAlwaysAuth != scope.get("npmAlwaysAuth", None):
        return False
    if template.requireNpmAuthToken and scope.get("npmAuthToken") is None:
        return False
    if template.requireNpmAuthToken and scope.get("npmAuthToken", "").strip() == "UPDATE WITH GITHUB ACCESS TOKEN":
        return False
    return True


def yarnrc_contains_scope(yarnrc: Dict[str, Any], scope: YarnNpmScope) -> bool:
    yarnrc_scopes = yarnrc.get("npmScopes", {})
    yarnrc_scope = yarnrc_scopes.get(scope.name)
    if yarnrc_scope is None:
        return False

    return match_scope(scope, yarnrc_scope)


class YarnNpmScopeConfigured(Check):
    name = "yarn.npmScopeConfigured"

    def __init__(self, scope: YarnNpmScope, tokenInstructions: Optional[str] = None):
        self.scope = scope
        self.yarnrc_suggestion = get_yarnrc_suggestion(scope)
        tokenInstructionString = f"\n\n{tokenInstructions}" if tokenInstructions else ""
        self.suggestions = {OS.GENERIC: f"""Add the lines below to ~/.yarnrc.yml:

{self.yarnrc_suggestion}{tokenInstructionString}"""}

    def check(self) -> CheckResult:
        try:
            yarnrc = get_yarnrc_contents()
        except Exception as e:
            return self.failed(str(e))

        if not yarnrc_contains_scope(yarnrc, self.scope):
            return self.failed(f"Scope {self.scope.name} not configured in yarnrc")

        return self.passed(f"Scope {self.scope.name} configured in yarnrc")


class YarnNpmGithubTokenValid(Check):
    name = "yarn.npmGithubTokenValid"
    depends_on = [YarnNpmScopeConfigured]

    def __init__(self, github_org: str, scope_name: str):
        self.scope_name = scope_name
        self.github_organisation = github_org
        self.suggestions = {
            OS.GENERIC: "Please check the token was copied correctly from GitHub."
            " Ensure the token hasn't expired, or has been revoked."
            " Also, ensure it has the correct permissions to read packages."
        }

    def check(self) -> CheckResult:
        try:
            github_token = get_yarnrc_token_for_scope(self.scope_name)
        except Exception as e:
            return self.failed(str(e))
        headers = {
            "Authorization": f"Bearer {github_token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        logging.debug(f"Checking the validity of Yarn token {github_token} with the Github API")
        response = requests.get(
            f"https://api.github.com/orgs/{self.github_organisation}/packages?package_type=npm", headers=headers
        )
        if response.status_code == 200:
            logging.debug(f"API call returned: {response.text}")
            return self.passed("Github Yarn token is valid")
        else:
            return self.failed(f"Github Yarn token is not valid: {response.text}")


def get_yarnrc_contents() -> dict:
    yarnrc_path = get_yarnrc_path()
    if not file_exists(yarnrc_path):
        raise Exception(f"{yarnrc_path} does not exist")

    try:
        with open(yarnrc_path, "rb") as yarnrc_file:
            return yaml.safe_load(yarnrc_file)
    except YAMLError:
        logging.error(f"Exception reading {yarnrc_path}", exc_info=True)
        raise Exception("Failed to parse yarnrc")


def get_yarnrc_token_for_scope(scope_name: str) -> Optional[str]:
    yarnrc = get_yarnrc_contents()
    yarnrc_scopes = yarnrc.get("npmScopes", {})
    yarnrc_scope = yarnrc_scopes.get(scope_name)
    if yarnrc_scope is None:
        raise Exception(f"Scope {scope_name} not configured in yarnrc")

    return yarnrc_scope.get("npmAuthToken", None)

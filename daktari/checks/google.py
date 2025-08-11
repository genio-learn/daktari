import json
import logging
import os.path
from json import JSONDecodeError
from typing import Optional

from daktari.check import Check, CheckResult
from daktari.command_utils import can_run_command
from daktari.file_utils import file_exists
from daktari.os import OS
from daktari.version_utils import get_simple_cli_version


class GoogleCloudSdkInstalled(Check):
    name = "google.cloudSdkInstalled"

    suggestions = {
        OS.OS_X: """<cmd>brew install --cask google-cloud-sdk</cmd>

Then, add the gcloud components to your PATH.

For bash users, add this to ~/.bashrc:
source "$(brew --prefix)/Caskroom/google-cloud-sdk/latest/google-cloud-sdk/path.bash.inc"

For zsh users, add this to ~/.zhsrc:
source "$(brew --prefix)/Caskroom/google-cloud-sdk/latest/google-cloud-sdk/path.zsh.inc\" """,
        OS.UBUNTU: "<cmd>sudo snap install google-cloud-sdk --classic</cmd>",
        OS.GENERIC: "Install gcloud: https://cloud.google.com/sdk/docs/quickstart",
    }

    def check(self) -> CheckResult:
        return self.verify(can_run_command("gcloud --version"), "Google Cloud SDK is <not/> installed and on $PATH")


class CloudSqlProxyInstalled(Check):
    name = "google.cloudSqlProxyInstalled"

    def __init__(self, required_version: Optional[str] = None, recommended_version: Optional[str] = None):
        self.required_version = required_version
        self.recommended_version = recommended_version

    suggestions = {
        OS.GENERIC: "Install Cloud SQL Proxy: <cmd>gcloud components install cloud-sql-proxy</cmd>",
    }

    def check(self) -> CheckResult:
        installed_version = get_simple_cli_version("cloud-sql-proxy")
        return self.validate_semver_expression(
            "cloud-sql-proxy", installed_version, self.required_version, self.recommended_version
        )


class GkeGcloudAuthPluginInstalled(Check):
    name = "google.gkeGcloudAuthPluginInstalled"
    depends_on = [GoogleCloudSdkInstalled]

    suggestions = {
        OS.UBUNTU: "<cmd>sudo apt-get install google-cloud-sdk-gke-gcloud-auth-plugin</cmd>",
        OS.GENERIC: "<cmd>gcloud components install gke-gcloud-auth-plugin</cmd>",
    }

    def check(self) -> CheckResult:
        return self.verify(can_run_command("gke-gcloud-auth-plugin --version "), "GKE auth plugin is <not/> installed")


class DockerGoogleCloudAuthConfigured(Check):
    name = "google.dockerGCloudAuthConfigured"
    depends_on = [GoogleCloudSdkInstalled]

    def __init__(self, cloud_project, region, registry):
        self.registry = registry
        self.suggestions = {
            OS.GENERIC: f"""
                Setup gcloud authentication and docker credential helper for gcloud.
                The following commands will open your browser and ask you to login and approve.
                Run:
                <cmd>rm -r ~/.config/gcloud</cmd>
                <cmd>gcloud auth login</cmd>
                <cmd>gcloud config set project {cloud_project}</cmd>
                <cmd>gcloud config set --quiet compute/zone {region}</cmd>
                <cmd>gcloud auth application-default login</cmd>
                <cmd>gcloud auth configure-docker {registry}</cmd>
                """
        }

    def check(self) -> CheckResult:
        # Logged in with gcloud
        google_config_path = os.path.expanduser("~/.config/gcloud/application_default_credentials.json")
        if not file_exists(google_config_path):
            return self.failed(f"{google_config_path} does not exist")

        if not can_run_command("gcloud auth application-default print-access-token"):
            return self.failed("Application Default Credentials are not correctly set up")

        # Docker configured correctly
        docker_config_path = os.path.expanduser("~/.docker/config.json")
        if not file_exists(docker_config_path):
            return self.failed(f"{docker_config_path} does not exist")

        try:
            with open(docker_config_path, "rb") as docker_config_file:
                docker_config = json.load(docker_config_file)
        except IOError:
            logging.error(f"Exception reading {docker_config_path}", exc_info=True)
            return self.failed(f"Failed to read {docker_config_path}")
        except JSONDecodeError:
            logging.error(f"Exception parsing {docker_config_path}", exc_info=True)
            return self.failed(f"Failed to parse {docker_config_path}")

        if docker_config.get("credHelpers", {}).get(self.registry) != "gcloud":
            return self.failed("docker gcloud auth for {self.registry} not configured")

        return self.passed("docker gcloud auth configured")

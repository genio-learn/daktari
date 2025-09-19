import logging
from typing import Optional

from daktari.check import Check, CheckResult
from daktari.command_utils import can_run_command, get_stdout
from daktari.file_utils import file_contains_text, is_ascii
from daktari.os import OS
from daktari.version_utils import get_simple_cli_version


class GitInstalled(Check):
    name = "git.installed"

    suggestions = {
        OS.OS_X: "<cmd>brew install git</cmd>",
        OS.UBUNTU: "<cmd>sudo apt install git</cmd>",
        OS.GENERIC: "Install Git: https://git-scm.com/downloads",
    }

    def check(self) -> CheckResult:
        if can_run_command("git version"):
            return self.passed("Git is installed")
        else:
            return self.failed("Could not find git on the path")


class GitLfsInstalled(Check):
    name = "git.lfs.installed"
    depends_on = [GitInstalled]

    suggestions = {
        OS.OS_X: "<cmd>brew install git-lfs</cmd>",
        OS.UBUNTU: "<cmd>sudo apt install git-lfs</cmd>",
        OS.GENERIC: "Install Git LFS: https://github.com/git-lfs/git-lfs/wiki/Installation",
    }

    def check(self) -> CheckResult:
        return self.verify(can_run_command("git lfs version"), "Git LFS is <not/> installed")


class GitLfsSetUpForUser(Check):
    name = "git.lfs.setUpForUser"
    depends_on = [GitLfsInstalled]

    suggestions = {
        OS.GENERIC: """
            Set up Git LFS for your user account:
            <cmd>git lfs install</cmd>
            """
    }

    def check(self) -> CheckResult:
        output = get_stdout("git lfs env")
        passed = bool(output and "git-lfs filter-process" in output)
        return self.verify(passed, "Git LFS is <not/> set up for the current user")


class GitLfsFilesDownloaded(Check):
    name = "git.lfs.filesDownloaded"
    depends_on = [GitLfsSetUpForUser]

    suggestions = {
        OS.GENERIC: """
            Download all Git LFS files and update working copy with the downloaded content:
            <cmd>git lfs pull</cmd>
            """
    }

    def check(self) -> CheckResult:
        output = get_stdout("git lfs ls-files") or ""
        files_not_downloaded = [line.split()[2] for line in output.splitlines() if line.split()[1] == "-"]
        for file in files_not_downloaded:
            logging.info(f"Git LFS file not downloaded: {file}")
        passed = len(files_not_downloaded) == 0
        return self.verify(passed, "Git LFS files have <not/> been downloaded")


class GitCryptInstalled(Check):
    name = "git.crypt.installed"
    depends_on = [GitInstalled]

    suggestions = {
        OS.OS_X: "<cmd>brew install git-crypt</cmd>",
        OS.UBUNTU: "<cmd>sudo apt install git-crypt</cmd>",
        OS.GENERIC: "Install git-crypt: https://www.agwa.name/projects/git-crypt/",
    }

    def check(self) -> CheckResult:
        return self.verify(can_run_command("git crypt version"), "git-crypt is <not/> installed")


class GitCryptUnlocked(Check):
    name = "git.crypt.unlocked"
    depends_on = [GitCryptInstalled]

    def __init__(self, fileToCheck: str):
        self.fileToCheck = fileToCheck

    suggestions = {
        OS.GENERIC: """
            Unlock this repository with:
            <cmd>git-crypt unlock</cmd>
            """,
    }

    def check(self) -> CheckResult:
        is_unlocked = is_ascii(self.fileToCheck)
        return self.verify(is_unlocked, "Encrypted files have <not/> been unlocked")


class PreCommitInstalled(Check):
    name = "preCommit.installed"
    depends_on = [GitInstalled]

    def __init__(self, required_version: Optional[str] = None, recommended_version: Optional[str] = None):
        self.required_version = required_version
        self.recommended_version = recommended_version

    suggestions = {
        OS.OS_X: "<cmd>brew install pre-commit</cmd>",
        OS.GENERIC: "Install pre-commit: https://pre-commit.com/#installation",
    }

    def check(self) -> CheckResult:
        installed_version = get_simple_cli_version("pre-commit")
        return self.validate_semver_expression(
            "pre-commit", installed_version, self.required_version, self.recommended_version
        )


class PreCommitGitHooksInstalled(Check):
    name = "preCommit.gitHooksInstalled"
    depends_on = [PreCommitInstalled]

    suggestions = {
        OS.GENERIC: "<cmd>pre-commit install</cmd>",
    }

    def check(self) -> CheckResult:
        git_hooks_installed = file_contains_text(".git/hooks/pre-commit", "pre-commit.com")
        return self.verify(git_hooks_installed, "pre-commit Git hooks are <not/> installed")


class GpgInstalled(Check):
    name = "gpg.installed"

    suggestions = {
        OS.OS_X: "<cmd>brew install gpg2 gnupg pinentry-mac</cmd>",
        OS.UBUNTU: "<cmd>sudo apt install gpg</cmd>",
        OS.GENERIC: "Install gpg: https://gnupg.org/",
    }

    def check(self) -> CheckResult:
        return self.verify_install("gpg")


class GitCommitSigningSetUp(Check):
    name = "git.commitSigningSetUp"

    suggestions = {
        OS.GENERIC: "Follow instructions to set up commit signing with 1Password: "
        "https://developer.1password.com/docs/ssh/git-commit-signing/",
    }

    def check(self) -> CheckResult:
        key = get_stdout("git config user.signingkey")
        passed = key is not None and key != ""
        return self.verify(passed, "user.signingkey is <not/> set")


class GitCommitAutoSigningEnabled(Check):
    name = "git.commitAutoSigningEnabled"
    depends_on = [GitCommitSigningSetUp]

    suggestions = {OS.GENERIC: "<cmd>git config commit.gpgsign true</cmd>"}

    def check(self) -> CheckResult:
        setting = get_stdout("git config commit.gpgsign")
        passed = setting == "true"
        return self.verify(passed, "commit.gpgsign is <not/> enabled")


class GitCommitSigningFormat(Check):
    name = "git.commitSigningFormat"

    def __init__(self, required_format: str, suggestion: str):
        self.required_format = required_format
        self.suggestions = {OS.GENERIC: suggestion}

    def check(self) -> CheckResult:
        format_setting = get_stdout("git config gpg.format")
        return self.verify(
            format_setting == self.required_format,
            f"gpg.format is {self.required_format}",
            f"gpg.format is not {self.required_format}: {format_setting}",
        )


class GitUserNameAndEmailConfigured(Check):
    name = "gitUserNameAndEmail.configured"
    depends_on = [GitInstalled]
    pass_fail_message = "git name and email are <not/> set"

    suggestions = {
        OS.GENERIC: """
            Configure git to use your name and email for commits. These should match your GitHub account.
            <cmd>git config --global user.name "Your Name"</cmd>
            <cmd>git config --global user.email "your.email@genio.co"</cmd>
            """,
    }

    def check(self):
        user_name = get_stdout("git config user.name")
        user_email = get_stdout("git config user.email")
        return self.verify(None not in (user_name, user_email), self.pass_fail_message)

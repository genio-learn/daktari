from daktari.check import Check, CheckResult
from daktari.file_utils import file_contains_text_regex, get_absolute_path
from daktari.os import OS, detect_os


def is_ssh_configured_to_use_macos_keychain(ssh_config_path: str = "~/.ssh/config") -> bool:
    absolute_ssh_config_path = get_absolute_path(ssh_config_path)
    return file_contains_text_regex(
        absolute_ssh_config_path, "IgnoreUnknown\\s+UseKeychain"
    ) and file_contains_text_regex(absolute_ssh_config_path, "UseKeychain\\s+yes")


class SSHConfigSetup(Check):
    name = "ssh.config.setup"

    suggestions = {OS.OS_X: """
            Add "IgnoreUnknown UseKeychain" and "UseKeychain yes" to ~/.ssh/config.
            E.g:
                Host *
                    IgnoreUnknown UseKeychain
                    UseKeychain yes
                    IdentityFile ~/.ssh/id_rsa
            """}

    def check(self) -> CheckResult:
        if detect_os() != OS.OS_X:
            return self.passed("Setup not required on non-Macbook devices")
        else:
            if not is_ssh_configured_to_use_macos_keychain():
                return self.failed("'IgnoreUnknown UseKeychain' or 'UseKeychain yes' not present in ~/.ssh/config")
            return self.passed("~/.ssh/config setup correctly")

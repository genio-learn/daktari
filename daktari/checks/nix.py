import os

from daktari.check import Check, CheckResult
from daktari.checks.direnv import DirenvAllowed
from daktari.os import OS


class NixInstalled(Check):
    name = "nix.installed"
    suggestions = {
        OS.GENERIC: """
            Install Determinate Nix, then open a new shell:
            <cmd>curl -fsSL https://install.determinate.systems/nix | sh -s -- install</cmd>
            """,
    }

    def check(self) -> CheckResult:
        return self.verify_install("nix")


class NixDevShellActive(Check):
    name = "nix.devShellActive"
    depends_on = [NixInstalled, DirenvAllowed]
    suggestions = {
        OS.GENERIC: """
            Hook direnv into your shell (https://direnv.net/docs/hook.html), then cd out of and back into the repo,
            or run: <cmd>direnv reload</cmd>
            """,
    }

    def check(self) -> CheckResult:
        return self.verify(os.getenv("IN_NIX_SHELL") is not None, "the Nix dev shell is <not/> active")


class AsdfNotOnPath(Check):
    name = "asdf.notOnPath"
    suggestions = {
        OS.GENERIC: "Uninstall asdf, or remove its shims directory from PATH in your shell config",
    }

    def check(self) -> CheckResult:
        return self.verify(
            ".asdf/shims" not in os.getenv("PATH", ""), "asdf shims are not on PATH", "asdf shims are on PATH"
        )

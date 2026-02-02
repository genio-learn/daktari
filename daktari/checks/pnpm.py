from daktari.check import Check, CheckResult
from daktari.os import OS


class PnpmInstalled(Check):
    name = "pnpm.installed"

    suggestions = {
        OS.OS_X: "<cmd>brew install pnpm</cmd>",
        OS.GENERIC: "<cmd>npm install -g pnpm</cmd>",
    }

    def check(self) -> CheckResult:
        return self.verify_install("pnpm")

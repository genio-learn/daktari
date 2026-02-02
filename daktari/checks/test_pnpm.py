import unittest
from unittest import mock

from daktari.check import CheckStatus
from daktari.checks.pnpm import PnpmInstalled


class TestPnpm(unittest.TestCase):
    @mock.patch("daktari.check.can_run_command")
    def test_pnpm_installed_returns_pass_when_installed(self, mock_can_run_command):
        mock_can_run_command.return_value = True
        result = PnpmInstalled().check()
        self.assertEqual(result.status, CheckStatus.PASS)
        mock_can_run_command.assert_called_once_with("pnpm --version")

    @mock.patch("daktari.check.can_run_command")
    def test_pnpm_installed_returns_fail_when_not_installed(self, mock_can_run_command):
        mock_can_run_command.return_value = False
        result = PnpmInstalled().check()
        self.assertEqual(result.status, CheckStatus.FAIL)
        mock_can_run_command.assert_called_once_with("pnpm --version")


if __name__ == "__main__":
    unittest.main()

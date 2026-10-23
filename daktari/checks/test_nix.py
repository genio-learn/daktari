import unittest
from unittest import mock

from daktari.check import CheckStatus
from daktari.checks.nix import AsdfNotOnPath, NixDevShellActive, NixInstalled


class TestNixInstalled(unittest.TestCase):
    @mock.patch("daktari.check.can_run_command", return_value=True)
    def test_passes_when_nix_runs(self, can_run_command):
        result = NixInstalled().check()
        self.assertEqual(result.status, CheckStatus.PASS)
        self.assertEqual(result.summary, "nix is installed")
        can_run_command.assert_called_once_with("nix --version")

    @mock.patch("daktari.check.can_run_command", return_value=False)
    def test_fails_when_nix_missing(self, can_run_command):
        result = NixInstalled().check()
        self.assertEqual(result.status, CheckStatus.FAIL)
        self.assertEqual(result.summary, "nix is not installed")


class TestNixDevShellActive(unittest.TestCase):
    @mock.patch.dict("os.environ", {"IN_NIX_SHELL": "impure"})
    def test_passes_in_nix_shell(self):
        result = NixDevShellActive().check()
        self.assertEqual(result.status, CheckStatus.PASS)
        self.assertEqual(result.summary, "the Nix dev shell is active")

    @mock.patch.dict("os.environ", {}, clear=True)
    def test_fails_outside_nix_shell(self):
        result = NixDevShellActive().check()
        self.assertEqual(result.status, CheckStatus.FAIL)
        self.assertEqual(result.summary, "the Nix dev shell is not active")


class TestAsdfNotOnPath(unittest.TestCase):
    @mock.patch.dict("os.environ", {"PATH": "/nix/store/abc/bin:/usr/bin"})
    def test_passes_without_asdf_shims(self):
        result = AsdfNotOnPath().check()
        self.assertEqual(result.status, CheckStatus.PASS)

    @mock.patch.dict("os.environ", {"PATH": "/Users/dev/.asdf/shims:/usr/bin"})
    def test_fails_with_asdf_shims(self):
        result = AsdfNotOnPath().check()
        self.assertEqual(result.status, CheckStatus.FAIL)
        self.assertEqual(result.summary, "asdf shims are on PATH")

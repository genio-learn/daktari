import unittest
from unittest import mock

from daktari.checks.onepassword import account_exists, contains_account, find_op_path


class TestOnePassword(unittest.TestCase):

    def test_account_exists(self):
        self.assertTrue(account_exists("checks/test_resources/op_config_with_account.json", "account-name"))
        self.assertFalse(
            account_exists("checks/test_resources/op_config_with_account.json", "non-existent-account-name")
        )

    def test_contains_account(self):
        account_url = "test.1password.com"

        correct_output = """
        URL                    EMAIL                        USER ID
        test.1password.com     test.email@domain.com        test-user-id
        """

        incorrect_output = """
        URL                    EMAIL                        USER ID
        my.1password.com       test.email@domain.com        test-user-id
        """

        empty_output = ""

        self.assertTrue(contains_account(correct_output, account_url))
        self.assertFalse(contains_account(incorrect_output, account_url))
        self.assertFalse(contains_account(empty_output, account_url))


class TestFindOpPath(unittest.TestCase):
    @mock.patch("daktari.checks.onepassword.get_stdout")
    @mock.patch("daktari.checks.onepassword.shutil.which", return_value="/home/dev/.cache/genio-nix/op-shadow/op")
    def test_uses_op_on_path(self, which, get_stdout):
        self.assertEqual(find_op_path(), "/home/dev/.cache/genio-nix/op-shadow/op")
        which.assert_called_once_with("op")
        get_stdout.assert_not_called()

    @mock.patch("daktari.checks.onepassword.get_stdout", return_value="/home/dev/.asdf/installs/op")
    @mock.patch("daktari.checks.onepassword.shutil.which", return_value="/home/dev/.asdf/shims/op")
    def test_resolves_asdf_shim(self, which, get_stdout):
        self.assertEqual(find_op_path(), "/home/dev/.asdf/installs/op")
        get_stdout.assert_called_once_with(["sh", "-c", "asdf which op"])

    @mock.patch("daktari.checks.onepassword.get_stdout")
    @mock.patch("daktari.checks.onepassword.shutil.which", return_value=None)
    def test_returns_none_when_op_missing(self, which, get_stdout):
        self.assertIsNone(find_op_path())
        get_stdout.assert_not_called()

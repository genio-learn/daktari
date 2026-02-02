import unittest
from unittest import mock

from daktari.check import CheckStatus
from daktari.checks.npmrc import (
    NpmrcScope,
    NpmrcScopeConfigured,
    NpmrcGithubTokenValid,
    get_registry_host,
    npmrc_contains_scope_registry,
    npmrc_contains_auth_token,
    npmrc_scope_is_configured,
    get_npmrc_suggestion,
)

TEST_SCOPE_NAME = "my-org"
TEST_REGISTRY = "https://npm.pkg.github.com"
TEST_REGISTRY_HOST = "npm.pkg.github.com"
TEST_AUTH_TOKEN = "ghp_abc123xyz"


class TestNpmrcHelpers(unittest.TestCase):
    def test_get_registry_host(self):
        self.assertEqual(get_registry_host("https://npm.pkg.github.com"), "npm.pkg.github.com")
        self.assertEqual(get_registry_host("https://registry.npmjs.org"), "registry.npmjs.org")
        self.assertEqual(get_registry_host("https://npm.example.com/custom/path"), "npm.example.com")

    def test_npmrc_contains_scope_registry_matching(self):
        scope = NpmrcScope(name=TEST_SCOPE_NAME, registry=TEST_REGISTRY)
        lines = [
            f"@{TEST_SCOPE_NAME}:registry={TEST_REGISTRY}\n",
            f"//{TEST_REGISTRY_HOST}/:_authToken={TEST_AUTH_TOKEN}\n",
        ]
        self.assertTrue(npmrc_contains_scope_registry(lines, scope))

    def test_npmrc_contains_scope_registry_not_matching(self):
        scope = NpmrcScope(name=TEST_SCOPE_NAME, registry=TEST_REGISTRY)
        lines = [
            "@other-scope:registry=https://registry.npmjs.org\n",
        ]
        self.assertFalse(npmrc_contains_scope_registry(lines, scope))

    def test_npmrc_contains_scope_registry_empty_lines(self):
        scope = NpmrcScope(name=TEST_SCOPE_NAME, registry=TEST_REGISTRY)
        lines = []
        self.assertFalse(npmrc_contains_scope_registry(lines, scope))

    def test_npmrc_contains_auth_token_matching(self):
        lines = [
            f"@{TEST_SCOPE_NAME}:registry={TEST_REGISTRY}\n",
            f"//{TEST_REGISTRY_HOST}/:_authToken={TEST_AUTH_TOKEN}\n",
        ]
        self.assertTrue(npmrc_contains_auth_token(lines, TEST_REGISTRY))

    def test_npmrc_contains_auth_token_not_matching(self):
        lines = [
            f"@{TEST_SCOPE_NAME}:registry={TEST_REGISTRY}\n",
            "//registry.npmjs.org/:_authToken=some-token\n",
        ]
        self.assertFalse(npmrc_contains_auth_token(lines, TEST_REGISTRY))

    def test_npmrc_contains_auth_token_placeholder_rejected(self):
        lines = [
            f"//{TEST_REGISTRY_HOST}/:_authToken=UPDATE_WITH_TOKEN\n",
        ]
        self.assertFalse(npmrc_contains_auth_token(lines, TEST_REGISTRY))

    def test_npmrc_contains_auth_token_empty_rejected(self):
        lines = [
            f"//{TEST_REGISTRY_HOST}/:_authToken=\n",
        ]
        self.assertFalse(npmrc_contains_auth_token(lines, TEST_REGISTRY))

    def test_npmrc_scope_is_configured_without_auth(self):
        scope = NpmrcScope(name=TEST_SCOPE_NAME, registry=TEST_REGISTRY, requireAuthToken=False)
        lines = [
            f"@{TEST_SCOPE_NAME}:registry={TEST_REGISTRY}\n",
        ]
        self.assertTrue(npmrc_scope_is_configured(lines, scope))

    def test_npmrc_scope_is_configured_with_auth_present(self):
        scope = NpmrcScope(name=TEST_SCOPE_NAME, registry=TEST_REGISTRY, requireAuthToken=True)
        lines = [
            f"@{TEST_SCOPE_NAME}:registry={TEST_REGISTRY}\n",
            f"//{TEST_REGISTRY_HOST}/:_authToken={TEST_AUTH_TOKEN}\n",
        ]
        self.assertTrue(npmrc_scope_is_configured(lines, scope))

    def test_npmrc_scope_is_configured_with_auth_missing(self):
        scope = NpmrcScope(name=TEST_SCOPE_NAME, registry=TEST_REGISTRY, requireAuthToken=True)
        lines = [
            f"@{TEST_SCOPE_NAME}:registry={TEST_REGISTRY}\n",
        ]
        self.assertFalse(npmrc_scope_is_configured(lines, scope))

    def test_npmrc_scope_is_configured_registry_missing(self):
        scope = NpmrcScope(name=TEST_SCOPE_NAME, registry=TEST_REGISTRY)
        lines = [
            f"//{TEST_REGISTRY_HOST}/:_authToken={TEST_AUTH_TOKEN}\n",
        ]
        self.assertFalse(npmrc_scope_is_configured(lines, scope))

    def test_get_npmrc_suggestion_without_auth(self):
        scope = NpmrcScope(name=TEST_SCOPE_NAME, registry=TEST_REGISTRY, requireAuthToken=False)
        suggestion = get_npmrc_suggestion(scope)
        self.assertEqual(suggestion, f"@{TEST_SCOPE_NAME}:registry={TEST_REGISTRY}")

    def test_get_npmrc_suggestion_with_auth(self):
        scope = NpmrcScope(name=TEST_SCOPE_NAME, registry=TEST_REGISTRY, requireAuthToken=True)
        suggestion = get_npmrc_suggestion(scope)
        expected = f"@{TEST_SCOPE_NAME}:registry={TEST_REGISTRY}\n//{TEST_REGISTRY_HOST}/:_authToken=UPDATE_WITH_TOKEN"
        self.assertEqual(suggestion, expected)


class TestNpmrcScopeConfigured(unittest.TestCase):
    @mock.patch("daktari.checks.npmrc.get_npmrc_contents")
    def test_returns_pass_when_scope_configured(self, mock_get_contents):
        mock_get_contents.return_value = [
            f"@{TEST_SCOPE_NAME}:registry={TEST_REGISTRY}\n",
            f"//{TEST_REGISTRY_HOST}/:_authToken={TEST_AUTH_TOKEN}\n",
        ]
        scope = NpmrcScope(name=TEST_SCOPE_NAME, registry=TEST_REGISTRY, requireAuthToken=True)
        result = NpmrcScopeConfigured(scope).check()
        self.assertEqual(result.status, CheckStatus.PASS)

    @mock.patch("daktari.checks.npmrc.get_npmrc_contents")
    def test_returns_fail_when_scope_not_configured(self, mock_get_contents):
        mock_get_contents.return_value = [
            "@other-scope:registry=https://registry.npmjs.org\n",
        ]
        scope = NpmrcScope(name=TEST_SCOPE_NAME, registry=TEST_REGISTRY)
        result = NpmrcScopeConfigured(scope).check()
        self.assertEqual(result.status, CheckStatus.FAIL)

    @mock.patch("daktari.checks.npmrc.get_npmrc_contents")
    def test_returns_fail_when_file_not_found(self, mock_get_contents):
        mock_get_contents.side_effect = Exception("~/.npmrc does not exist")
        scope = NpmrcScope(name=TEST_SCOPE_NAME, registry=TEST_REGISTRY)
        result = NpmrcScopeConfigured(scope).check()
        self.assertEqual(result.status, CheckStatus.FAIL)
        self.assertIn("does not exist", result.summary)


class TestNpmrcGithubTokenValid(unittest.TestCase):
    @mock.patch("daktari.checks.npmrc.can_run_command")
    def test_returns_pass_when_token_valid(self, mock_can_run):
        mock_can_run.return_value = True
        result = NpmrcGithubTokenValid(scope_name=TEST_SCOPE_NAME, test_package="some-package").check()
        self.assertEqual(result.status, CheckStatus.PASS)
        mock_can_run.assert_called_once_with(f"npm view @{TEST_SCOPE_NAME}/some-package version")

    @mock.patch("daktari.checks.npmrc.can_run_command")
    def test_returns_fail_when_token_invalid(self, mock_can_run):
        mock_can_run.return_value = False
        result = NpmrcGithubTokenValid(scope_name=TEST_SCOPE_NAME, test_package="some-package").check()
        self.assertEqual(result.status, CheckStatus.FAIL)
        mock_can_run.assert_called_once_with(f"npm view @{TEST_SCOPE_NAME}/some-package version")


if __name__ == "__main__":
    unittest.main()

import unittest
from unittest.mock import patch

from daktari.check import CheckStatus
from daktari.checks.git import PreCommitGitHooksInstalled

# The path git resolves the pre-commit hook to. In a worktree this is *not*
# ".git/hooks/pre-commit" (there ".git" is a file, not a directory), and when
# core.hooksPath is set it points outside the per-worktree gitdir entirely.
RESOLVED_HOOK_PATH = "/main/.git/hooks/pre-commit"
LITERAL_HOOK_PATH = ".git/hooks/pre-commit"


def fake_hook_contents(path: str, text: str) -> bool:
    """Model a worktree: only the git-resolved hook path exists and is installed.

    The literal ".git/hooks/pre-commit" path is absent (in a worktree ".git" is a
    file), so reading it directly always misses.
    """
    return path == RESOLVED_HOOK_PATH and text == "pre-commit.com"


class TestPreCommitGitHooksInstalled(unittest.TestCase):
    @patch("daktari.checks.git.file_contains_text", side_effect=fake_hook_contents)
    @patch("daktari.checks.git.get_stdout", return_value=RESOLVED_HOOK_PATH)
    def test_passes_in_worktree_when_hook_resolves_via_git(self, mock_get_stdout, mock_contains):
        result = PreCommitGitHooksInstalled().check()
        self.assertEqual(
            result.status,
            CheckStatus.PASS,
            "Hooks are installed (resolved via git), so the check should pass even in a worktree",
        )
        mock_get_stdout.assert_called_once_with("git rev-parse --git-path hooks/pre-commit")

    @patch("daktari.checks.git.file_contains_text", side_effect=fake_hook_contents)
    @patch("daktari.checks.git.get_stdout", return_value=RESOLVED_HOOK_PATH)
    def test_resolved_path_is_checked_not_literal(self, mock_get_stdout, mock_contains):
        PreCommitGitHooksInstalled().check()
        mock_contains.assert_called_once_with(RESOLVED_HOOK_PATH, "pre-commit.com")

    @patch("daktari.checks.git.file_contains_text", return_value=False)
    @patch("daktari.checks.git.get_stdout", return_value=RESOLVED_HOOK_PATH)
    def test_fails_when_hook_not_installed(self, mock_get_stdout, mock_contains):
        result = PreCommitGitHooksInstalled().check()
        self.assertEqual(result.status, CheckStatus.FAIL)

    @patch("daktari.checks.git.file_contains_text", return_value=False)
    @patch("daktari.checks.git.get_stdout", return_value=None)
    def test_fails_gracefully_when_git_cannot_resolve_path(self, mock_get_stdout, mock_contains):
        result = PreCommitGitHooksInstalled().check()
        self.assertEqual(result.status, CheckStatus.FAIL)


if __name__ == "__main__":
    unittest.main()

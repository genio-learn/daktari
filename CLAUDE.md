# CLAUDE.md

Daktari runs a series of checks (e.g. "is X installed", "is env var Y set") against a developer
machine and prints fix suggestions when a check fails. Projects consume it via a `.daktari.py`
config listing the checks they want.

## Versioning & releases

**Do not bump the version manually.** Versioning is fully automated: on every push to `main`,
`.github/workflows/release.yaml` runs the bumpversion action, which bumps the patch version,
commits, tags, builds, and publishes to PyPI. Leave `version`/`current_version` in
`pyproject.toml`, `daktari/__init__.py`, `README.md`, and `.bumpversion.cfg` untouched in PRs —
the release process owns them.

## Checks

Checks live in `daktari/checks/<area>.py` (e.g. `mobile.py`, `misc.py`) and subclass `Check`
(`daktari/check.py`). Group a new check with its peers by area. Each check has a dotted `name`
(e.g. `maestro.installed`) and OS-keyed `suggestions` (`OS.OS_X`, `OS.UBUNTU`, `OS.GENERIC`).

Prefer the `Check` base-class helpers over hand-rolled `run_command` + try/except:

- **Presence only:** `return self.verify_install("maestro")` — see `WatchmanInstalled`,
  `JqInstalled`.
- **Version-aware:** take optional `required_version` / `recommended_version` in `__init__`, then
  `validate_semver_expression("maestro", get_simple_cli_version("maestro"), self.required_version,
  self.recommended_version)` — see `KtlintInstalled`, `CmakeInstalled`, `MaestroInstalled`.
  `get_simple_cli_version` runs `<tool> --version` and parses the first semver-ish token, so it
  works for tools that print a bare version (`2.5.1`).
- **Boolean condition:** `self.verify(<bool>, "X is <not/> ok")` — the `<not/>` marker is rewritten
  for the pass vs. fail message.

`required_version` failing → FAIL; `recommended_version` failing → PASS_WITH_WARNING. When adding a
version constraint to a check that downstream configs already use, prefer `recommended_version`
(warn-only) to avoid turning a passing check into a hard failure on existing machines.

## Tests

`unittest` + `pytest`, colocated as `daktari/checks/test_<area>.py`. Mock at the point of use —
patch `daktari.checks.<area>.<symbol>` (e.g. `daktari.checks.mobile.get_simple_cli_version`), not
the symbol's defining module. Cover the pass and fail paths, plus version expressions for
version-aware checks. CI runs pytest from the `daktari/` working directory.

## Lint / format (must pass CI)

```
flake8 daktari            # max-line-length = 120, extend-ignore = E203
black -l 120 --check .
mypy daktari
```

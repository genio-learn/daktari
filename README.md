**Daktari** is a tool to help the initial setup and ongoing maintenance of developer environments. It runs a series of checks (for example, that required software is installed) and provides suggestions on how to fix the issue if the check fails.

## Configuration

In the root of the project repository, create a `.daktari.py` configuration file listing the checks you want run. For example,

```python
from daktari.checks.git import *

version = "0.0.281"
title = "My Project"

checks = [
    GitInstalled(),
    GitLfsInstalled(),
    GitLfsSetUpForUser(),
    GitLfsFilesDownloaded(),
    GitCryptInstalled(),
]
```

Then run `daktari` to diagnose your environment:

```
$ daktari
✅ [git.installed] Git is installed
✅ [git.lfs.installed] Git LFS is installed
✅ [git.lfs.setUpForUser] Git LFS is set up for the current user
✅ [git.lfs.filesDownloaded] Git LFS files have been downloaded
❌ [git.crypt.installed] git-crypt is not installed
┌─💡 Suggestion ─────────┐
│ brew install git-crypt │
└────────────────────────┘
```

## Custom Check

You can write a custom check as a Python class within `.daktari.py`, and include it in your list of checks. Example of a check implementation:

```python
class GitCryptInstalled(Check):
    name = "git.crypt.installed"
    depends_on = [GitInstalled]

    suggestions = {
        OS.OS_X: "<cmd>brew install git-crypt</cmd>",
        OS.UBUNTU: "<cmd>sudo apt install git-crypt</cmd>",
        OS.GENERIC: "Install git-crypt (https://www.agwa.name/projects/git-crypt/)",
    }

    def check(self):
        return self.verify(can_run_command("git crypt version"), "git-crypt is <not/> installed")
```

## Testing Daktari changes locally

Having cloned the repo into `~/daktari`, you can make use of PYTHONPATH to run daktari using your local changes.

To do this, navigate into a directory that has a `.daktari.py` (e.g. another repository intending to use your change) and run:

```bash
PYTHONPATH=~/daktari python3 -m daktari --debug
```

## Release instructions

Daktari is continuously deployed via a github action - see [release.yaml](.github/workflows/release.yaml). 
In case of a need to manually release, the steps are:

```
bumpversion --verbose patch
python -m build
twine check dist/*
twine upload dist/*
```

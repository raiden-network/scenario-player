import os
import re
import subprocess

REPO_OWNER = os.environ["CIRCLE_PROJECT_USERNAME"]
REPO_NAME = os.environ["CIRCLE_PROJECT_REPONAME"]

BUMPVERSION_CFG = os.environ.get("BUMPVERSION_CFG")
PROJECT_ROOT = os.environ["PROJECT_ROOT"]
COMMIT_SHA = os.environ["CIRCLE_SHA1"]

COMMIT_PATTERN = r"^\[(?P<TYPE>(FEAT|FIX|HOTFIX))-(?P<ISSUE>#\d+)\]\w?(?P<SUBJECT>.*$)"
RELEASE_COMMIT_PATTERN = r"^\[(?P<TYPE>RELEASE)\]\w?(?P<SUBJECT>)"
BUMPVERSION_PREFIX = "Cut New Release:"
CURRENT_BRANCH = os.environ.get("CIRCLE_BRANCH")

PROJECT_GIT_DIR = PROJECT_ROOT + "/.git"
# Data about the commit message.
COMMIT_MSG = subprocess.run(
    f"git --git-dir {PROJECT_GIT_DIR} log --format=oneline -n 1 {COMMIT_SHA} --format=%s".split(
        " "
    ),
    check=True,
    stdout=subprocess.PIPE,
).stdout.decode("UTF-8")

release_match = re.match(RELEASE_COMMIT_PATTERN, COMMIT_MSG, flags=re.IGNORECASE)
if release_match:
    release_match = release_match.groupdict()
else:
    release_match = {}

commit_match = re.match(COMMIT_PATTERN, COMMIT_MSG, flags=re.IGNORECASE)
if commit_match:
    commit_match = commit_match.groupdict()
else:
    if COMMIT_MSG.startswith(BUMPVERSION_PREFIX):
        commit_match = {"TYPE": "VERSION_BUMP"}
    else:
        commit_match = {}


COMMIT_ISSUE = commit_match.get("ISSUE", "")
COMMIT_TYPE = (commit_match.get("TYPE", "") or release_match.get("TYPE", "")).upper()


# GH API auth token.
GH_AUTH_TOKEN = os.environ["GITHUB_TOKEN"]
GH_AUTH_HEADERS = {"Authorization": f"token {GH_AUTH_TOKEN}"}

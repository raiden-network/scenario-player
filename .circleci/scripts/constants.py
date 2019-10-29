import enum
import os
import re
import subprocess


class COMMIT_TYPES(enum.Enum):
    FEAT = "feat"
    FIX = "fix"
    BUMP = "version_bump"


REPO_OWNER = os.environ["CIRCLE_PROJECT_USERNAME"]
REPO_NAME = os.environ["CIRCLE_PROJECT_REPONAME"]

BUMPVERSION_CFG = os.environ.get("BUMPVERSION_CFG")
PROJECT_ROOT = os.environ["PROJECT_ROOT"]
COMMIT_SHA = os.environ["CIRCLE_SHA1"]

COMMIT_PATTERN = r"^\[(?P<TYPE>(FEAT|FIX))-(?P<ISSUE>#\d+)\]\w?(?P<SUBJECT>.*$)"
BUMPVERSION_PREFIX = "Cut New Release:"
CURRENT_BRANCH = os.environ.get("CIRCLE_BRANCH")

PROJECT_GIT_DIR = PROJECT_ROOT + "/.git"

# Commit message and its components.
git_log_output = subprocess.run(
    f"git --git-dir {PROJECT_GIT_DIR} log "
    f"--format=oneline -n 1 {COMMIT_SHA} --format=%s".split(" "),
    check=True,
    stdout=subprocess.PIPE,
)
COMMIT_MSG = git_log_output.stdout.decode("UTF-8")

commit_match = re.match(COMMIT_PATTERN, COMMIT_MSG, flags=re.IGNORECASE) or {}
if commit_match:
    commit_match = commit_match.groupdict()

parsed_type = commit_match.get("TYPE")
if parsed_type == "FEAT":
    COMMIT_TYPE = COMMIT_TYPES.FEAT
elif parsed_type == "FIX":
    COMMIT_TYPE = COMMIT_TYPES.FIX
elif COMMIT_MSG.startswith(BUMPVERSION_PREFIX):
    COMMIT_TYPE = COMMIT_TYPES.BUMP
else:
    COMMIT_TYPE = None

COMMIT_ISSUE = commit_match.get("ISSUE")
COMMIT_SUBJECT = commit_match.get("SUBJECT")

# GH API auth token.
GH_AUTH_TOKEN = os.environ["GITHUB_TOKEN"]
GH_AUTH_HEADERS = {"Authorization": f"token {GH_AUTH_TOKEN}"}

import os

import subprocess
from constants import (
    CURRENT_BRANCH,
    PROJECT_ROOT,
    GH_AUTH_HEADERS,
    REPO_OWNER,
    REPO_NAME,
    PROJECT_GIT_DIR,
    BUMPVERSION_CFG,
    COMMIT_TYPE,
)

import requests

from scenario_player import __version__

CI_CONFIG_DIR = os.environ["CI_CONFIG_DIR"]


print(f"Bumping branch {CURRENT_BRANCH}..")


def get_last_tag():
    return subprocess.run("git describe --tags".split(" "), check=True, stdout=subprocess.PIPE).stdout.decode("UTF-8")


part = ""
bump_release_type = None
if CURRENT_BRANCH in ("dev", "release"):
    part = "iteration"
    # Make sure we set the correct release type.
    if CURRENT_BRANCH == "dev" and "dev" not in __version__:
        bump_release_type = "dev"
    elif CURRENT_BRANCH == 'release' and "rc" not in __version__:
        bump_release_type = "rc"

elif CURRENT_BRANCH == "master":
    # Get all commits of the release branch that was merged. If no release
    # branch exists, we assume this was a hotfix merge.
    resp = requests.get(
        f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/branches",
        headers=GH_AUTH_HEADERS,
    )
    branches = [branch["name"] for branch in resp.json()]
    print("Available branches: ", branches)
    part = "patch"

    if "release" in branches and COMMIT_TYPE == "RELEASE":
        print("Found a 'release' branch, checking for feature commits..")
        process_output = subprocess.run(
            f"git --git-dir={PROJECT_GIT_DIR} log {CURRENT_BRANCH}~1..origin/release --format=%s".split(" "),
            check=True,
            stdout=subprocess.PIPE,
        )
        stdout_decoded = process_output.stdout.decode("UTF-8")
        for line in stdout_decoded.split("\n"):
            if "FEAT" in line:
                print("Feature commit detected:\n{line}\nChanging bump type to 'minor'..")
                part = "minor"
                break


print(f"Bumping part {part}..")


if bump_release_type:
    r = subprocess.run(
        f"bumpversion --config-file={BUMPVERSION_CFG} --current-version={__version__} release_type".split(" "),
        check=True, stdout=subprocess.PIPE,
    )
else:
    r = subprocess.run(
        f"bumpversion --config-file={BUMPVERSION_CFG} --current-version={__version__} {part}".split(" "),
        check=True, stdout=subprocess.PIPE,
    )

print("Push Bump commit..")
subprocess.run(f"git --git-dir={PROJECT_GIT_DIR} push --set-upstream origin {CURRENT_BRANCH}".split(" "), check=True)

print("Push Bump tag..")
subprocess.run(f"git --git-dir={PROJECT_GIT_DIR} push -u --tags origin".split(" "), check=True)

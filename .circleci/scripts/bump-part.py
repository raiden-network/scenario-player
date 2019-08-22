import os
import subprocess

import requests
from constants import (
    BUMPVERSION_CFG,
    COMMIT_TYPE,
    CURRENT_BRANCH,
    GH_AUTH_HEADERS,
    PROJECT_GIT_DIR,
    PROJECT_ROOT,
    REPO_NAME,
    REPO_OWNER,
)
from chlogger import make_chlog

from scenario_player import __version__

CI_CONFIG_DIR = os.environ["CI_CONFIG_DIR"]


print(f"Bumping branch {CURRENT_BRANCH}..")

if COMMIT_TYPE == "VERSION_BUMP":
    print("This is already a version bump - skip bumping.")
    exit()


def get_last_tag():
    return subprocess.run(
        "git describe --tags".split(" "), check=True, stdout=subprocess.PIPE
    ).stdout.decode("UTF-8")


part = ""
bump_release_type = None
if CURRENT_BRANCH == "dev":
    part = "iteration"
    # Make sure we set the correct release type.
    if "dev" not in __version__:
        bump_release_type = "dev"

elif CURRENT_BRANCH == "master":
    # Get all commits of the release branch that was merged. If no release
    # branch exists, we assume this was a hotfix merge.
    resp = requests.get(
        f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/branches", headers=GH_AUTH_HEADERS
    )
    branches = [branch["name"] for branch in resp.json()]
    print("Available branches: ", branches)
    part = "patch"

    if COMMIT_TYPE == "RELEASE":
        print("Detected RELEASE, checking for feature commits..")
        process_output = subprocess.run(
            f"git --git-dir={PROJECT_GIT_DIR} log {CURRENT_BRANCH}~1..origin/dev --format=%s".split(
                " "
            ),
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
        f"bumpversion --config-file={BUMPVERSION_CFG} --current-version={__version__} release_type".split(
            " "
        ),
        check=True,
        stdout=subprocess.PIPE,
    )
else:
    r = subprocess.run(
        f"bumpversion --config-file={BUMPVERSION_CFG} --current-version={__version__} {part}".split(
            " "
        ),
        check=True,
        stdout=subprocess.PIPE,
    )

if CURRENT_BRANCH == "master" and COMMIT_TYPE == "RELEASE":
    r = subprocess.run(f"git --git-dir={PROJECT_GIT_DIR} describe --abbrev=0 --tags", check=True)
    tag = r.stdout.decode("UTF-8").strip(" ").strip("\n")
    make_chlog(Path(f"{PROJECT_ROOT}/CHANGES.rst"), new_version=tag)

print("Push Bump commit..")
subprocess.run(
    f"git --git-dir={PROJECT_GIT_DIR} push --set-upstream origin {CURRENT_BRANCH}".split(" "),
    check=True,
)

print("Push Bump tag..")
subprocess.run(f"git --git-dir={PROJECT_GIT_DIR} push -u --tags origin".split(" "), check=True)

if CURRENT_BRANCH == "master":
    # Sync up our versions between dev and master. The actual bump to dev's tag will be done
    # on the next merge commit to it.
    subprocess.run(f"git --git-dir={PROJECT_GIT_DIR} checkout dev".split(" "), check=True)
    subprocess.run(f"git --git-dir={PROJECT_GIT_DIR} pull".split(" "), check=True)
    subprocess.run(f"git --git-dir={PROJECT_GIT_DIR} checkout master .bumpversion.cfg".split(" "), check=True)
    subprocess.run(f"git --git-dir={PROJECT_GIT_DIR} checkout master scenario_player/__init__.py".split(" "), check=True)
    subprocess.run(f"git --git-dir={PROJECT_GIT_DIR} commit .bumpversion.cfg scenario_player/__init__.py -m".split(" ") + ["'Sync Branch Versions.'"], check=True)
    subprocess.run(f"git --git-dir={PROJECT_GIT_DIR} push".split(" "), check=True)

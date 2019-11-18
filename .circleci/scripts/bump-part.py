import os
import subprocess

from constants import (
    BUMPVERSION_CFG,
    COMMIT_TYPE,
    COMMIT_ISSUE,
    COMMIT_SUBJECT,
    COMMIT_TYPES,
    CURRENT_BRANCH,
    PROJECT_GIT_DIR,
)

from scenario_player import __version__

CI_CONFIG_DIR = os.environ["CI_CONFIG_DIR"]


parts = {
    COMMIT_TYPES.FEAT: "minor",
    COMMIT_TYPES.FIX: "patch",
    COMMIT_TYPES.BUMP: "bump_version",
}

PART = parts[COMMIT_TYPE]

if CURRENT_BRANCH != "master":
    print("Skipping non-master branch.")
    exit(0)
elif COMMIT_TYPE is None or COMMIT_ISSUE is None or COMMIT_SUBJECT is None:
    print(
        "Skipping bumping because one of TYPE/ISSUE/SUBJECT was not given or "
        "could not be parsed from the commit title."
    )
    exit(3)
elif COMMIT_TYPE is COMMIT_TYPES.BUMP:
    print("Skipping commit, as it's already a version bump commit itself.")
    exit(0)

print(f"Bumping part {PART} on branch '{CURRENT_BRANCH}'..")


r = subprocess.run(
    f"bumpversion --config-file={BUMPVERSION_CFG} "
    f"--current-version={__version__} {PART}".split(" "),
    check=True,
    stdout=subprocess.PIPE,
)


print("Push Bump commit..")
subprocess.run(
    f"git --git-dir={PROJECT_GIT_DIR} push --set-upstream origin {CURRENT_BRANCH}".split(" "),
    check=True,
)

print("Push Bump tag..")
subprocess.run(f"git --git-dir={PROJECT_GIT_DIR} push -u --tags origin".split(" "), check=True)

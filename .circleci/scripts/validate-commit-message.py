#!/usr/bin/env python3


from constants import COMMIT_MSG, COMMIT_TYPE, CURRENT_BRANCH

print(f"Validating commit message {COMMIT_MSG!r}")
print(f"Parsed commit type: {COMMIT_TYPE}")

if CURRENT_BRANCH not in ("master", "dev"):
    # This workflow is executed on a PR - we skip validation for these.
    exit(0)

if not COMMIT_TYPE:
    # The commit message title does not comply with any of our regexes.
    print("No commit type parsed - the commit message does not comply with the required pattern!")
    exit(1)

if COMMIT_TYPE == "VERSION_BUMP":
    print("Commit by bumpversion tool detected, skipping validation..")
elif CURRENT_BRANCH == "master" and COMMIT_TYPE not in ("HOTFIX", "RELEASE"):
    print("`master` branch allows  hotfixes (HOTFIX) and releases (RELEASE) only!")
    exit(1)

# Message seems to check out.
exit(0)

#!/usr/bin/env python3


from constants import COMMIT_TYPE, CURRENT_BRANCH

if not COMMIT_TYPE:
    # The commit message title does not comply with any of our regexes.
    exit(1)

if COMMIT_TYPE == "VERSION_BUMP":
    exit(0)

if CURRENT_BRANCH == "release" and COMMIT_TYPE == "FEAT":
    print("No feature (FEAT) commits allowed on `release` branches!")
    exit(1)

if CURRENT_BRANCH == "master" and COMMIT_TYPE not in ("HOTFIX", "RELEASE"):
    print("`master` branch allows  hotfixes (HOTFIX) and releases (RELEASE) only!")
    exit(1)

# Message seems to check out.
exit(0)

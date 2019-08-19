"""TODO: This script is a stub."""
import re
import subprocess

from typing import List, Tuple

from constants import PROJECT_GIT_DIR, CURRENT_BRANCH, COMMIT_PATTERN


if CURRENT_BRANCH != "master":
    exit(0)


def latest_tag():
    proc =subprocess.run(
        f"git --git-dir={PROJECT_GIT_DIR} tag -l".split(" "),
        check=True,
        stdout=subprocess.PIPE,
    )

    all_tags = proc.stdout.decode("UTF-8").split("\n")
    releases = sorted([tag for tag in all_tags if 'dev' not in tag and tag.startswith("v")], reverse=True)
    latest, *_ = releases
    return latest


def read_git_commit_history_since_tag(tag) -> Tuple[List[Tuple[str, str]], List[Tuple[str, str]], List[Tuple[str, str]]]:
    """Return a list of all git commit titles since the given `tag`.

    If `tag` is not given, we'll use the previous tag and compare the log up
    up to the current tag.

    The commits are returned as three lists:
        1. feature commits
        2. bugfix commits
        3. hotfix commits
    """
    completed_process = subprocess.run(
        f"git --git-dir={PROJECT_GIT_DIR} log master..{tag} --format=%s".split(" "),
        check=True,
        stdout=subprocess.PIPE,
    )
    titles = completed_process.stdout.decode("UTF-8").split("\n")

    completed_process = subprocess.run(
        f"git --git-dir={PROJECT_GIT_DIR} log master..{tag} --format=%b".split(" "),
        check=True,
        stdout=subprocess.PIPE,
    )
    bodies = completed_process.stdout.decode("UTF-8").split("\n")

    assert len(titles) == len(bodies)

    pattern = re.compile(COMMIT_PATTERN)

    feats, fixes, hotfixes = [], [], []

    for title, body in zip(titles, bodies):
        match = pattern.match(title)
        if not match:
            continue

        commit_type = match.groupdict()["TYPE"]

        if commit_type == "FEAT":
            feats.append((title, body))
        elif commit_type == "FIX":
            fixes.append((title, body))
        elif commit_type == "HOTFIX":
            hotfixes.append((title, body))
        else:
            print(f"No type found, skipping commit '{title}'..")

    return feats, fixes, hotfixes


def format_commits(*commits: List[Tuple[str, str]]) -> List[str]:
    """Format the given commits for writing to the Changelog.

    The expected input str format is:

        [(FEAT|FIX|HOTFIX)-#123] <Subject>

        <Optional body with further details on the commit.>

    The output format is as follows::

        - #123 <Subject>
            <Optional body with further details on the commit.>

    """


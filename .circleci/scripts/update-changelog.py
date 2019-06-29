"""TODO: This script is a stub."""
from typing import List, Tuple
from constants import PROJECT_GIT_DIR, CURRENT_BRANCH


if CURRENT_BRANCH != "master":
    exit(0)


def read_git_commit_history_since_tag(tag=None) -> Tuple[List[str], List[str], List[str]]:
    """Return a list of all git commit titles since the given `tag`.

    If `tag` is not given, we'll use the previous tag and compare the log up
    up to the current tag.

    The commits are returned as three lists:
        feature commits
        2. bugfix commits
        3. hotfix commits
    """
    completed_process = subprocess.run(
        f"git --git-dir={PROJECT_GIT_DIR} log master..release --format=%s".split(" "),
        check=True,
        stdout=subprocess.PIPE,
    )
    titles = completed_process.stdout.decode("UTF-8").split("\n")

    completed_process = subprocess.run(
        f"git --git-dir={PROJECT_GIT_DIR} log master..release --format=%b".split(" "),
        check=True,
        stdout=subprocess.PIPE,
    )
    bodies = completed_process.stdout.decode("UTF-8").split("\n")


def format_commits(*commits) -> List[str]:
    """Format the given commits for writing to the Changelog.

    The expected input str format is:

        [(FEAT|FIX|HOTFIX)-#123] <Subject>

        <Optional body with further details on the commit.>

    The output format is as follows::

        - #123 <Subject>
            <Optional body with further details on the commit.>

    """


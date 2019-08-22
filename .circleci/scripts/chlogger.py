"""TODO: This script is a stub."""
import pathlib
import re
import subprocess

from typing import List, Set, Tuple
from constants import PROJECT_GIT_DIR, CURRENT_BRANCH, COMMIT_PATTERN, COMMIT_TYPE


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
        f"git --git-dir={PROJECT_GIT_DIR} log {tag}..master --format=%s".split(" "),
        check=True,
        stdout=subprocess.PIPE,
    )
    titles = completed_process.stdout.decode("UTF-8").split("\n")

    # The body of a commit may include newline characters, so we need to specify
    # a custom separator to indicate the end of the commit body.
    separator = "<><><>"
    completed_process = subprocess.run(
        f"git --git-dir={PROJECT_GIT_DIR} log {tag}..master --format=%b{separator}".split(" "),
        check=True,
        stdout=subprocess.PIPE,
    )
    bodies = completed_process.stdout.decode("UTF-8").split(separator)

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

    print("feats", feats)
    print("fixes", fixes)
    print("hotfixes", hotfixes)

    return feats, fixes, hotfixes


def format_commits(commits: List[Tuple[str, str]]) -> List[str]:
    """Format the given commits for writing to the Changelog.

    The expected input Tuple[str, str] format is:

        ([(FEAT|FIX|HOTFIX)-#123] <Subject>, <Optional body with further details on the commit.>)

    The output format is as follows::

        r'- #123 <Subject>\n    <Optional body with further details on the commit.>\n'

    Newlines in the body are honored, and each line indented by 4 spaces automatically.
    TODO: Duplicate Issues should share a single Changelog Entry.
    """
    if not commits:
        return []
    pattern = re.compile(COMMIT_PATTERN)
    formatted = set()
    print("UNPACKING", commits)
    for title, body in commits:
        match = pattern.match(title)
        issue, subject = match.groupdict()["ISSUE"], match.groupdict()["SUBJECT"]

        entry = f"- {issue} {subject}\n"

        if body:
            # Make sure the body is indented by 8 spaces.
            formatted_body = "        ".join(body.split("\n"))
            entry += f"{formatted_body}\n"
        formatted.add(entry)
    return sorted(formatted)


def update_chlog(tag: str, feats: List[str], fixes: List[str], hotfixes: List[str], chlog_path: pathlib.Path = pathlib.Path("CHANGELOG.rst")):
    try:
        history = chlog_path.read_text()
    except FileNotFoundError:
        print("No Changelog file found - creating a new one.")
        history = ""

    chlog_entry = f"RELEASE {tag}\n=============\n\n"

    if feats:
        feats = "\n".join(feats)
        chlog_entry += f"Features\n--------\n{feats}\n"""

    if fixes:
        fixes = "\n".join(fixes)

        chlog_entry += f"Fixes\n-----\n{fixes}\n"

    if hotfixes:
        hotfixes = "\n".join(hotfixes)

        chlog_entry += f"Hotfixes\n--------\n{hotfixes}\n"
    chlog_path.write_text(f"{chlog_entry}\n{history}")


def make_chlog(chlog_path, new_version):
    feats, fixes, hotfixes = read_git_commit_history_since_tag(new_version)
    update_chlog("0.4.0", format_commits(feats), format_commits(fixes), format_commits(hotfixes), chlog_path)

    subprocess.run(f"git --git-dir={PROJECT_GIT_DIR} git add CHANGELOG.rst".split(" "), check=True)
    subprocess.run(f"git --git-dir={PROJECT_GIT_DIR} git commit CHANGELOG.rst -m \"Update Changelog.\"".split(" "), check=True)

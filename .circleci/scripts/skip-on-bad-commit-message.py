import subprocess

try:
    subprocess.run("python ${CI_SCRIPTS_DIR}/validate-commit-message.py".split(), check=True)
except subprocess.SubprocessError:
    # The commit message is bogus, so we skip the current step.
    subprocess.run("circleci step halt".split())
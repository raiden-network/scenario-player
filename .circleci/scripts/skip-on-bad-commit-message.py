import subprocess

try:
    subprocess.run("python validate-commit-message.py".split(), check=True)
except subprocess.SubprocessError:
    # The commit message is bogus, so we skip the current step.
    subprocess.run("circle step halt".split())
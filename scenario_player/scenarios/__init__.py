import pathlib
import subprocess
import sys


def run_builtin_scenarios():
    abs_path = pathlib.Path(__file__).resolve().parent
    for file in abs_path:
        subprocess.call("scenario-player", *sys.argv, file.resolve())

    for file in abs_path:
        subprocess.call("scenario-player", *sys.argv, file.resolve(), "reclaim-eth")

from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from scenario_player import main
from scenario_player.exceptions.cli import WrongPassword

KEYSTORE_PATH = Path(__file__).resolve().parent.joinpath("keystore")
SCENARIO = f"{Path(__file__).parent.joinpath('scenario', 'join-network-scenario-J1.yaml')}"
CLI_ARGS = (
    f"--chain goerli:http://geth.goerli.ethnodes.brainbot.com:8545 "
    f"--keystore-file {KEYSTORE_PATH.joinpath('UTC--1')} "
    f"--no-ui "
    f"{{pw_option}} "
    f"{SCENARIO}"
)


@pytest.fixture(scope="module")
def runner():
    return CliRunner()


class Sentinel(Exception):
    pass


class TestPasswordHandling:
    # use a fixture instead of patch directly,
    # to avoid having to pass an extra argument to all methods.
    @pytest.fixture(autouse=True)
    def patch_collect_tasks_on_setup(self):
        with patch("scenario_player.main.collect_tasks", side_effect=Sentinel):
            # Yield instead of return,
            # as that allows the patching to be undone after the test is complete.
            yield

    def test_password_file_not_existent(self, runner):
        """A not existing password file should raise error"""
        result = runner.invoke(
            main.run, CLI_ARGS.format(pw_option=f"--password-file /does/not/exist").split(" ")
        )
        assert result.exit_code == 2
        assert '"--password-file": File "/does/not/exist" does not exist.' in result.output

    def test_mutually_exclusive(self, runner):
        result = runner.invoke(
            main.run,
            CLI_ARGS.format(
                pw_option=f"--password-file {KEYSTORE_PATH.joinpath('password')} --password 123"
            ).split(" "),
        )
        assert result.exit_code == 2
        assert "Error: Illegal usage: password_file is mutually exclusive" in result.output

    @pytest.mark.parametrize(
        "password_file, expected_exec",
        argvalues=[("wrong_password", WrongPassword), ("password", Sentinel)],
        ids=["wrong password", "correct password"],
    )
    def test_password_file(self, password_file, expected_exec, runner):
        result = runner.invoke(
            main.run,
            CLI_ARGS.format(pw_option=f"--password-file {KEYSTORE_PATH.joinpath(password_file)}"),
        )
        assert result.exc_info[0] == expected_exec
        assert result.exit_code == 1

    @pytest.mark.parametrize(
        "password, expected_exc",
        argvalues=[("wrong_password", WrongPassword), ("123", Sentinel)],
        ids=["wrong password", "correct password"],
    )
    def test_password(self, password, expected_exc, runner):
        result = runner.invoke(
            main.run, CLI_ARGS.format(pw_option=f"--password {password}").split(" ")
        )
        assert result.exc_info[0] == expected_exc
        assert result.exit_code == 1

    @pytest.mark.parametrize(
        "user_input, expected_exc",
        argvalues=[("wrongpassword", WrongPassword), ("123", Sentinel)],
        ids=["wrong password", "correct password"],
    )
    def test_manual_password_validation(self, user_input, expected_exc, runner):
        result = runner.invoke(
            main.run, CLI_ARGS.format(pw_option=f"--password {user_input}").split(" ")
        )
        assert result.exc_info[0] == expected_exc
        assert result.exit_code == 1

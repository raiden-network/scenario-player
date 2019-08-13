from pathlib import Path

import pytest
from click.testing import CliRunner

from scenario_player import main
from scenario_player.exceptions import ScenarioError
from scenario_player.exceptions.cli import WrongPassword


@pytest.fixture(scope="module")
def runner():
    return CliRunner()


KEYSTORE_PATH = str(Path(__file__).resolve().parents[0].joinpath("keystore"))
CLI_ARGS = [
    "--chain",
    "goerli:http://geth.goerli.ethnodes.brainbot.com:8545",
    "run",
    "--keystore-file",
    KEYSTORE_PATH + "/UTC--1",
    "--no-ui",
    # Here goes password config
    str(Path(__file__).resolve().parents[0].joinpath("scenario/join-network-scenario-J1.yaml"))
]


class TestPasswordHandling:

    def test_password_file_not_existent(self, runner):
        """A not existing password file should raise error"""
        result = runner.invoke(
            main.main,
            CLI_ARGS[:-1] + ["--password-file", "/does/not/exist"] + CLI_ARGS[-1:]
        )
        assert result.exit_code == 2
        assert '"--password-file": File "/does/not/exist" does not exist.' in result.output

    def test_wrong_password_file(self, runner):
        result = runner.invoke(
            main.main,
            CLI_ARGS[:-1] + ["--password-file", KEYSTORE_PATH + "/wrong_password"] + CLI_ARGS[-1:]
        )
        assert result.exit_code == 1
        assert result.exc_info[0] == WrongPassword

    def test_correct_password_file(self, runner):
        result = runner.invoke(
            main.main,
            CLI_ARGS[:-1] + ["--password-file", KEYSTORE_PATH + "/password"] + CLI_ARGS[-1:]
        )
        assert result.exit_code == 1
        assert result.exc_info[0] == ScenarioError
        assert "Insufficient balance (0.0 Eth) in account" in result.exc_info[1].args[0]

    def test_wrong_password(self, runner):
        result = runner.invoke(
            main.main,
            CLI_ARGS[:-1] + ["--password", "Wrong_Password"] + CLI_ARGS[-1:]
        )
        assert result.exit_code == 1
        assert result.exc_info[0] == WrongPassword

    def test_correct_password(self, runner):
        result = runner.invoke(
            main.main,
            CLI_ARGS[:-1] + ["--password", "123"] + CLI_ARGS[-1:]
        )
        assert result.exit_code == 1
        assert result.exc_info[0] == ScenarioError
        assert "Insufficient balance (0.0 Eth) in account" in result.exc_info[1].args[0]

    def test_mutually_exclustive(self, runner):
        result = runner.invoke(
            main.main,
            CLI_ARGS[:-1] +
            ["--password-file", KEYSTORE_PATH + "/password"] +
            ["--password", "123"] +
            CLI_ARGS[-1:]
        )
        assert result.exit_code == 2
        assert 'Error: Illegal usage: password_file is mutually exclusive' in result.output

    def test_wrong_manual_password(self, runner):
        result = runner.invoke(
            main.main,
            CLI_ARGS,
            input="WrongPassword"
        )
        assert result.exit_code == 1
        assert result.exc_info[0] == WrongPassword

    def test_correct_manual_password(self, runner):
        result = runner.invoke(
            main.main,
            CLI_ARGS,
            input="123"
        )
        assert result.exit_code == 1
        assert result.exc_info[0] == ScenarioError
        assert "Insufficient balance (0.0 Eth) in account" in result.exc_info[1].args[0]

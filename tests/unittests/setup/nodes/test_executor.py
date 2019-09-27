import pytest
from unittest.mock import patch, PropertyMock
import subprocess

from scenario_player.setup.nodes.executor import ClientExecutor


class Sentinel(Exception):
    pass


@patch("scenario_player.setup.nodes.executor.mirakuru.HTTPExecutor.stop")
@patch("scenario_player.setup.nodes.executor.ClientExecutor._timeout", new_callable=PropertyMock(return_value=300))
def test_stop_restores_customized_timeout_on_exception(mock_prop, mock_stop):
    instance = ClientExecutor(["geth", "version"])
    mock_stop.side_effect = Sentinel
    expected = 10
    with pytest.raises(Sentinel):
        instance.stop(timeout=66)
    assert instance._timeout == expected
    mock_prop.assert_any_call(66)
    mock_prop.assert_any_call(300)


def test_instance_using_default_parameters_has_expected_timeout_set():
    instance = ClientExecutor(["geth", "version"])
    assert instance._timeout == 300, "Unexpected default value!"


@patch("scenario_player.setup.nodes.executor.subprocess.Popen")
def test_start_method_sets_stdout_and_stderr_to_pipe_by_default(mock_popen):
    instance = ClientExecutor(["geth", "version"])
    mock_popen.side_effect = Sentinel
    with pytest.raises(Sentinel):
        instance.start()

    _, kwargs = mock_popen.call_args
    assert kwargs["stdout"] == subprocess.PIPE
    assert kwargs["stderr"] == subprocess.PIPE


@patch("scenario_player.setup.nodes.executor.subprocess.Popen")
def test_start_method_allows_customizing_stderr_and_stdout(mock_popen):
    instance = ClientExecutor(["geth", "version"])
    mock_popen.side_effect = Sentinel
    out, err = object(), object()
    with pytest.raises(Sentinel):
        instance.start(stdout=out, stderr=err)

    _, kwargs = mock_popen.call_args
    assert kwargs["stdout"] == out
    assert kwargs["stderr"] == err

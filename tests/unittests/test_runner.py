from unittest import mock

import pytest
import requests

from scenario_player.runner import ScenarioRunner, TokenNetworkDiscoveryTimeout


# FIXME: Use :mod:`responses` instead!
class MockResponse:
    def __init__(self, status=200, payload=None):
        self.status_code = status
        self.payload = payload or "0x12AE66CDc592e10B60f9097a7b0D3C59fce29876"

    def raise_for_status(self):
        if self.status_code > 399:
            raise requests.HTTPError(response=self)

    def json(self):
        return self.payload


@pytest.fixture
def response():
    return MockResponse()


@pytest.fixture
def runner(dummy_scenario_runner):
    runner = ScenarioRunner.__new__(ScenarioRunner)

    # Monkeypatch the instance using the dummy_scenario_runner
    for attr, value in dummy_scenario_runner.__dict__.items():
        setattr(runner, attr, value)
    yield runner


@mock.patch("scenario_player.runner.Session.get")
class TestScenarioRunner:
    @pytest.mark.token_network_discovery
    def test_wait_for_token_discovery_raises_error_after_timeout_threshold_is_crossed(
        self, mock_request, response, runner
    ):
        response.status_code = 404
        mock_request.return_value = response

        with pytest.raises(TokenNetworkDiscoveryTimeout):
            runner.wait_for_token_network_discovery("test_node")

    def test_wait_for_token_network_discovery_returns_checksum_when_network_is_discovered(
        self, mock_request, response, runner
    ):
        mock_request.return_value = response
        actual = runner.wait_for_token_network_discovery("test_node")
        assert actual == response.payload

    @pytest.mark.token_network_discovery
    @pytest.mark.parametrize(
        "code, should_raise_http_error", argvalues=[(404, False), (500, True), (400, True)]
    )
    def test_wait_for_token_network_discovery_only_handles_404_status_codes_on_http_errors(
        self, mock_request, code, should_raise_http_error, runner
    ):
        response = MockResponse(code)

        # In case no error is expected, we need this response to avoid triggering a timeout.
        sentinel_response = MockResponse()

        mock_request.side_effect = (response, sentinel_response)

        try:
            runner.wait_for_token_network_discovery("test_node")
        except requests.HTTPError:
            if should_raise_http_error:
                return
            pytest.fail("DID RAISE HTTPError!")

    @pytest.mark.token_network_discovery
    @pytest.mark.parametrize(
        "returned, is_checksum",
        argvalues=[
            ("Totally not a checksum address", False),
            ("0x12AE66CDc592e10B60f9097a7b0D3C59fce29876", True),
        ],
    )
    def test_wait_for_token_network_discovery_raises_error_when_200_response_returns_non_checksum_address(
        self, mock_request, returned, is_checksum, response, runner
    ):
        response.payload = returned
        mock_request.return_value = response

        # Somehow, wrapping a pytest.raises() block instead always raised a false positive.
        try:
            runner.wait_for_token_network_discovery("test_node")
        except TypeError as e:
            if not is_checksum:
                # Should have raised the TypeError, all good.
                return
            pytest.fail(f"DID RAISE {e!r}")

    @mock.patch("scenario_player.runner.ScenarioRunner.wait_for_token_network_discovery")
    def test_ensure_token_network_discovery_checks_all_nodes_for_discovery(self, mock_wait_for_token_network_discovery, _, runner):
        """All nodes must have discovered the token network - make sure it checks
        all of them accordingly."""
        runner.node_controller = [mock.MagicMock(base_url="node1"), mock.MagicMock(base_url="node2"), mock.MagicMock(base_url="node3")]
        runner.ensure_token_network_discovery()

        for node in runner.node_controller:
            mock_wait_for_token_network_discovery.assert_any_call(node.base_url)


def test_runner_local_seed(runner, tmp_path):
    """Ensure the ``.local_seed`` property creates the seed file inside the ``.base_path``."""
    runner.base_path = tmp_path
    seed_file = tmp_path.joinpath("seed.txt")

    assert not seed_file.exists()

    runner_seed = runner.local_seed

    assert seed_file.exists()
    assert runner_seed == seed_file.read_text().strip()

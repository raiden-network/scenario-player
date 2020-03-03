from unittest import mock

import pytest
import requests

from scenario_player.runner import ScenarioRunner, TokenNetworkDiscoveryTimeout


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


def test_runner_local_seed(runner, tmp_path):
    """Ensure the ``.local_seed`` property creates the seed file inside the ``.base_path``."""
    runner.base_path = tmp_path
    seed_file = tmp_path.joinpath("seed.txt")

    assert not seed_file.exists()

    runner_seed = runner.local_seed

    assert seed_file.exists()
    assert runner_seed == seed_file.read_text().strip()

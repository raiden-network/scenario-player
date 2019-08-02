from collections import defaultdict

import pytest
import requests
import responses
from eth_utils.address import to_checksum_address


@pytest.fixture
def minimal_yaml_dict():
    """A dictionary with the minimum required keys for instantiating any ConfigMapping."""
    return {
        "scenario": {"serial": {"runner": None, "config": "salami"}},
        "settings": {},
        "token": {},
        "nodes": {"count": 1},
        "spaas": {},
    }


class DummyTokenContract:
    def __init__(self, token_address):
        self.checksum_address = to_checksum_address(token_address)
        self.address = token_address


class DummySettingsConfig:
    def __init__(self):
        self.timeout = 2


class DummyScenarioYAML:
    def __init__(self, scenario_name):
        self.name = scenario_name
        self.settings = DummySettingsConfig()


class DummyScenarioRunner:
    def __init__(self, scenario_name, token_address):
        self.scenario_name = scenario_name
        self.yaml = DummyScenarioYAML(scenario_name)
        self.session = requests.Session()
        self.task_cache = {}
        self.task_storage = defaultdict(dict)
        self.task_count = 0
        self.running_task_count = 0
        self.run_number = 0
        self.protocol = "http"
        self.token = DummyTokenContract(token_address)

    def task_state_changed(self, task, new_state):
        pass

    def get_node_baseurl(self, index):
        return f"{index}"

    def get_node_address(self, index):
        return f"0x2{index:039d}"


@pytest.fixture
def mocked_responses():
    with responses.RequestsMock() as requests_mock:
        yield requests_mock


@pytest.fixture
def dummy_scenario_runner(mocked_responses):
    return DummyScenarioRunner("dummy_scenario", f"0x1{1:039d}")

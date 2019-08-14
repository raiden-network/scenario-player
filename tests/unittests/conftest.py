from collections import defaultdict
from unittest.mock import MagicMock

import pytest
import requests
import responses
from eth_utils.address import to_checksum_address
from raiden_contracts.contract_manager import ContractManager

from raiden.network.rpc.client import JSONRPCClient
from scenario_player.constants import GAS_LIMIT_FOR_TOKEN_CONTRACT_CALL


@pytest.fixture
def minimal_yaml_dict():
    """A dictionary with the minimum required keys for instantiating any ConfigMapping."""
    return {
        "scenario": {"serial": {"tasks": {"wait_blocks": {"blocks": 5}}}},
        "settings": {},
        "token": {},
        "nodes": {"count": 1},
        "spaas": {},
    }


class DummyTokenContract:
    def __init__(self, token_address):
        self.checksum_address = to_checksum_address(token_address)
        self.address = token_address


class DummyRPCConfig:
    def __init__(self):
        self.client_id = "the_client_id"


class DummyServicesConfig:
    def __init__(self):
        self.rpc = DummyRPCConfig()


class DummySettingsConfig:
    def __init__(self):
        self.timeout = 2
        self.services = DummyServicesConfig()


class DummyTokenConfig:
    def __init__(self):
        self.address = "the_token_config_address"


class DummyScenarioYAML:
    def __init__(self, scenario_name):
        self.name = scenario_name
        self.settings = DummySettingsConfig()
        self.token = DummyTokenConfig()
        self.gas_limit = GAS_LIMIT_FOR_TOKEN_CONTRACT_CALL * 2


class DummyScenarioRunner:
    def __init__(self, scenario_name, token_address):
        self.client = MagicMock(spec=JSONRPCClient)
        self.contract_manager = MagicMock(spec=ContractManager)
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

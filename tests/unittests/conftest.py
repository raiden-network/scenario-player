from collections import defaultdict
from typing import Dict
from unittest.mock import MagicMock

import pytest
import requests
import responses
from eth_typing import ChecksumAddress
from eth_utils.address import to_checksum_address
from raiden_contracts.contract_manager import ContractManager
from tests.unittests.constants import TEST_TOKEN_ADDRESS, TEST_TOKEN_NETWORK_ADDRESS

from raiden.network.rpc.client import JSONRPCClient
from raiden.utils.formatting import to_canonical_address
from raiden.utils.typing import Address
from scenario_player.constants import GAS_LIMIT_FOR_TOKEN_CONTRACT_CALL
from scenario_player.tasks.base import Task


@pytest.fixture
def minimal_definition_dict():
    """A dictionary with the minimum required keys for instantiating any ConfigMapping."""
    return {
        "scenario": {"serial": {"tasks": {"wait_blocks": {"blocks": 5}}}},
        "settings": {},
        "token": {},
        "nodes": {"count": 1},
    }


class DummyTokenContract:
    def __init__(self, token_address: Address):
        self.checksum_address = to_checksum_address(token_address)
        self.address = token_address


class DummyRPCConfig:
    def __init__(self):
        self.client_id = "the_client_id"


class DummyPFSConfig:
    url = "http://pfs"


class DummyServicesConfig:
    def __init__(self):
        self.pfs = DummyPFSConfig()


@pytest.fixture
def dummy_settings_config(tmp_path):
    class DummySettingsConfig:
        def __init__(self):
            self.timeout = 2
            self.services = DummyServicesConfig()
            self.sp_root_dir = tmp_path
            self.sp_scenario_root_dir = tmp_path.joinpath("scenarios")
            self.sp_scenario_root_dir.mkdir(exist_ok=True, parents=True)

    return DummySettingsConfig()


class DummyTokenConfig:
    def __init__(self):
        self.address = "the_token_config_address"


@pytest.fixture
def dummy_scenario_definition(dummy_settings_config):
    class DummyScenarioDefinition:
        def __init__(self, scenario_name):
            self.name = scenario_name
            self.settings = dummy_settings_config
            self.token = DummyTokenConfig()
            self.gas_limit = GAS_LIMIT_FOR_TOKEN_CONTRACT_CALL * 2
            self.scenario_dir = dummy_settings_config.sp_scenario_root_dir.joinpath(self.name)
            self.scenario_dir.mkdir(parents=True, exist_ok=True)

    return DummyScenarioDefinition


class DummyNodeRunner:
    def __init__(self, index):
        self.index = index
        self.base_url = index

    @property
    def address(self):
        return f"0x1{self.index:039d}"


class DummyNodeController:
    def __init__(self, node_count: int):
        self.node_count = node_count

    def __getitem__(self, item):
        if int(item) >= self.node_count:
            raise IndexError()
        return DummyNodeRunner(item)

    def __len__(self):
        return self.node_count

    @property
    def address_to_index(self) -> Dict[ChecksumAddress, int]:
        return {runner.address: i for i, runner in enumerate(iter(self))}  # type: ignore


@pytest.fixture
def mocked_scenario_runner(dummy_scenario_definition):
    class DummyScenarioRunner:
        def __init__(
            self,
            scenario_name: str,
            token_address: Address,
            token_network_address: ChecksumAddress = TEST_TOKEN_NETWORK_ADDRESS,
            node_count: int = 4,
        ):
            self.client = MagicMock(spec=JSONRPCClient)
            self.contract_manager = MagicMock(spec=ContractManager)
            self.scenario_name = scenario_name
            self.definition = dummy_scenario_definition(scenario_name)
            self.session = requests.Session()
            self.task_cache: Dict[str, Task] = {}
            self.task_storage: Dict[str, dict] = defaultdict(dict)
            self.task_count = 0
            self.running_task_count = 0
            self.run_number = 0
            self.protocol = "http"
            self.token = DummyTokenContract(token_address)
            self.token_network_address = token_network_address
            self.node_controller = DummyNodeController(node_count)

        def task_state_changed(self, task, new_state):
            pass

        def get_node_baseurl(self, index):
            return f"{index}"

        def get_node_address(self, index):
            return self.node_controller[index].address

    return DummyScenarioRunner


@pytest.fixture
def mocked_responses():
    with responses.RequestsMock() as requests_mock:
        yield requests_mock


@pytest.fixture
def dummy_scenario_runner(mocked_responses, mocked_scenario_runner):
    return mocked_scenario_runner("dummy_scenario", to_canonical_address(TEST_TOKEN_ADDRESS))

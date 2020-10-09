from typing import Any, Dict, List, cast

import structlog
from eth_abi.codec import ABICodec
from eth_utils import encode_hex, event_abi_to_log_topic, to_canonical_address, to_checksum_address
from raiden_contracts.constants import (
    CONTRACT_MONITORING_SERVICE,
    CONTRACT_TOKEN_NETWORK,
    MonitoringServiceEvent,
)
from raiden_contracts.contract_manager import ContractManager, get_contracts_deployment_info
from web3 import Web3
from web3._utils.abi import filter_by_type
from web3._utils.events import get_event_data
from web3.types import FilterParams, LogReceipt

from raiden.settings import RAIDEN_CONTRACT_VERSION
from raiden.utils.typing import ABI, Address, BlockNumber
from scenario_player import runner as scenario_runner
from scenario_player.exceptions import ScenarioAssertionError, ScenarioError
from scenario_player.tasks.base import Task
from scenario_player.tasks.channels import STORAGE_KEY_CHANNEL_INFO

log = structlog.get_logger(__name__)


def decode_event(abi_codec: ABICodec, abi: ABI, log_: LogReceipt) -> Dict:
    """Helper function to unpack event data using a provided ABI

    Args:
        abi_codec: The ABI codec
        abi: The ABI of the contract, not the ABI of the event
        log_: The raw event data

    Returns:
        The decoded event
    """
    event_id = log_["topics"][0]
    events = filter_by_type("event", abi)
    topic_to_event_abi = {
        event_abi_to_log_topic(event_abi): event_abi for event_abi in events  # type: ignore
    }
    event_abi = topic_to_event_abi[event_id]
    event_data = get_event_data(abi_codec=abi_codec, event_abi=event_abi, log_entry=log_)
    return cast(Dict[Any, Any], event_data)


def query_blockchain_events(
    web3: Web3,
    contract_manager: ContractManager,
    contract_address: Address,
    contract_name: str,
    topics: List,
    from_block: BlockNumber,
    to_block: BlockNumber,
) -> List[Dict]:
    """Returns events emmitted by a contract for a given event name, within a certain range.

    Args:
        web3: A Web3 instance
        contract_manager: A contract manager
        contract_address: The address of the contract to be filtered, can be `None`
        contract_name: The name of the contract
        topics: The topics to filter for
        from_block: The block to start search events
        to_block: The block to stop searching for events

    Returns:
        All matching events
    """
    filter_params = FilterParams(
        {
            "fromBlock": from_block,
            "toBlock": to_block,
            "address": to_checksum_address(contract_address),
            "topics": topics,
        }
    )

    events = web3.eth.getLogs(filter_params)

    contract_abi = contract_manager.get_contract_abi(contract_name)
    return [
        decode_event(abi_codec=web3.codec, abi=contract_abi, log_=raw_event)
        for raw_event in events
    ]


class AssertBlockchainEventsTask(Task):
    """Assert on blockchain events.

    Required parameters:
      - ``contract_name``
        Which contract events to assert on. Example: ``TokenNetwork``
      - ``event_name``
        Contract specific event name to filter for.
      - ``num_events``
        The number of expected events.

    Optional parameters:
      - ``event_args``
        A dictionary of event specific arguments that is used to further filter the found events.
        This has a special handling for node addresses: If the name of an argument contains the
        word ``participant`` an integer node index can be given instead of an ethereum address.

    Example::

        - assert_events:
            contract_name: "TokenNetwork"
            event_name: "ChannelClosed"
            num_events: 1
            event_args: {closing_participant: 1}  # The 1 refers to scenario node index 1

    """

    _name = "assert_events"
    SYNCHRONIZATION_TIME_SECONDS = 0
    DEFAULT_TIMEOUT = 5 * 60  # 5 minutes

    def __init__(
        self, runner: scenario_runner.ScenarioRunner, config: Any, parent: "Task" = None
    ) -> None:
        super().__init__(runner, config, parent)

        required_keys = ["contract_name", "event_name", "num_events"]
        all_required_options_provided = all(key in config.keys() for key in required_keys)
        if not all_required_options_provided:
            raise ScenarioError(
                "Not all required keys provided. Required: " + ", ".join(required_keys)
            )

        self.contract_name = config["contract_name"]
        self.event_name = config["event_name"]
        self.num_events = config["num_events"]
        self.event_args: Dict[str, Any] = config.get("event_args", {}).copy()

        self.web3 = self._runner.client.web3

    def _run(self, *args, **kwargs):  # pylint: disable=unused-argument
        # get the correct contract address
        # this has to be done in `_run`, otherwise `_runner` is not initialized yet
        contract_data = get_contracts_deployment_info(
            chain_id=self._runner.definition.settings.chain_id, version=RAIDEN_CONTRACT_VERSION
        )
        if self.contract_name == CONTRACT_TOKEN_NETWORK:
            self.contract_address = self._runner.token_network_address
        else:
            try:
                assert contract_data
                contract_info = contract_data["contracts"][self.contract_name]
                self.contract_address = to_checksum_address(contract_info["address"])
            except KeyError:
                raise ScenarioError(f"Unknown contract name: {self.contract_name}")

        assert self.contract_address, "Contract address not set"
        events = query_blockchain_events(
            web3=self.web3,
            contract_manager=self._runner.contract_manager,
            contract_address=to_canonical_address(self.contract_address),
            contract_name=self.contract_name,
            topics=[],
            from_block=BlockNumber(self._runner.block_execution_started),
            to_block=BlockNumber(self.web3.eth.blockNumber),
        )

        # Filter matching events
        events = [e for e in events if e["event"] == self.event_name]

        if self.event_args:
            for key, value in self.event_args.items():
                if "participant" in key:
                    if isinstance(value, int) or (isinstance(value, str) and value.isnumeric()):
                        # Replace node index with eth address
                        self.event_args[key] = self._runner.get_node_address(int(value))

            event_args_items = self.event_args.items()
            # Filter the events by the given event args.
            # `.items()` produces a set like object which supports intersection (`&`)
            events = [e for e in events if e["args"] and event_args_items & e["args"].items()]

        # Raise exception when events do not match
        if not self.num_events == len(events):
            raise ScenarioAssertionError(
                f"Expected number of events ({self.num_events}) did not match the number "
                f"of events found ({len(events)})"
            )

        return {"events": events}


class AssertMSClaimTask(Task):
    _name = "assert_ms_claim"
    SYNCHRONIZATION_TIME_SECONDS = 0
    DEFAULT_TIMEOUT = 5 * 60  # 5 minutes

    def __init__(
        self, runner: scenario_runner.ScenarioRunner, config: Any, parent: Task = None
    ) -> None:
        super().__init__(runner, config, parent)

        required_keys = {"channel_info_key"}
        if not required_keys.issubset(config.keys()):
            raise ScenarioError(
                f'Not all required keys provided. Required: {", ".join(required_keys)}'
            )

        self.web3 = self._runner.client.web3
        self.contract_name = CONTRACT_MONITORING_SERVICE

        # get the MS contract address
        contract_data = get_contracts_deployment_info(
            chain_id=self._runner.definition.settings.chain_id, version=RAIDEN_CONTRACT_VERSION
        )
        assert contract_data
        try:
            contract_info = contract_data["contracts"][self.contract_name]
            self.contract_address = contract_info["address"]
        except KeyError:
            raise ScenarioError(f"Unknown contract name: {self.contract_name}")

    def _run(self, *args, **kwargs):  # pylint: disable=unused-argument
        channel_infos = self._runner.task_storage[STORAGE_KEY_CHANNEL_INFO].get(
            self._config["channel_info_key"]
        )

        if channel_infos is None:
            raise ScenarioError(
                f"No stored channel info found for key '{self._config['channel_info_key']}'."
            )

        # calculate reward_id
        assert "token_network_address" in channel_infos.keys()
        assert "channel_identifier" in channel_infos.keys()

        reward_id = bytes(
            Web3.soliditySha3(  # pylint: disable=no-value-for-parameter
                ["uint256", "address"],
                [int(channel_infos["channel_identifier"]), channel_infos["token_network_address"]],
            )
        )

        log.info("Calculated reward ID", reward_id=encode_hex(reward_id))

        events = query_blockchain_events(
            web3=self.web3,
            contract_manager=self._runner.contract_manager,
            contract_address=to_canonical_address(self.contract_address),
            contract_name=self.contract_name,
            topics=[],
            from_block=BlockNumber(self._runner.block_execution_started),
            to_block=BlockNumber(self.web3.eth.blockNumber),
        )

        # Filter matching events
        def match_event(event: Dict):
            if not event["event"] == MonitoringServiceEvent.REWARD_CLAIMED:
                return False

            event_reward_id = bytes(event["args"]["reward_identifier"])
            return event_reward_id == reward_id

        events = [e for e in events if match_event(e)]
        log.info("Matching events", events=events)

        must_claim = self._config.get("must_claim", True)
        found_events = len(events) > 0

        # Raise exception when no event was found
        if must_claim and not found_events:
            raise ScenarioAssertionError("No RewardClaimed event found for this channel.")
        elif not must_claim and found_events:
            raise ScenarioAssertionError("Unexpected RewardClaimed event found for this channel.")

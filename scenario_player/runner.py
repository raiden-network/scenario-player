from __future__ import annotations

import random
import time
from collections import defaultdict
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Dict, List, Optional, Set, Tuple

import gevent
import structlog
from eth_typing import ChecksumAddress
from eth_utils import encode_hex, is_checksum_address, to_checksum_address
from raiden_contracts.contract_manager import ContractManager, contracts_precompiled_path
from requests import HTTPError, RequestException, Session
from web3 import HTTPProvider, Web3

from raiden.accounts import Account
from raiden.constants import GAS_LIMIT_FOR_TOKEN_CONTRACT_CALL
from raiden.network.rpc.client import JSONRPCClient
from raiden.network.rpc.smartcontract_proxy import ContractProxy
from raiden.utils.typing import TransactionHash
from scenario_player.constants import (
    API_URL_TOKEN_NETWORK_ADDRESS,
    API_URL_TOKENS,
    NODE_ACCOUNT_BALANCE_FUND,
    NODE_ACCOUNT_BALANCE_MIN,
    OWN_ACCOUNT_BALANCE_MIN,
)
from scenario_player.exceptions import ScenarioError, TokenRegistrationError
from scenario_player.exceptions.legacy import TokenNetworkDiscoveryTimeout
from scenario_player.scenario import ScenarioYAML
from scenario_player.services.rpc.utils import assign_rpc_instance_id
from scenario_player.services.utils.interface import ServiceInterface
from scenario_player.utils import TimeOutHTTPAdapter, get_udc_and_token, wait_for_txs
from scenario_player.utils.token import Token, UserDepositContract

if TYPE_CHECKING:
    from scenario_player.tasks.base import Task, TaskState

log = structlog.get_logger(__name__)


class ScenarioRunner:
    def __init__(
        self,
        account: Account,
        chain_urls: Dict[str, List[str]],
        auth: str,
        data_path: Path,
        scenario_file: Path,
        task_state_callback: Optional[
            Callable[["ScenarioRunner", "Task", "TaskState"], None]
        ] = None,
    ):
        from scenario_player.node_support import RaidenReleaseKeeper, NodeController

        self.auth = auth

        self.release_keeper = RaidenReleaseKeeper(data_path.joinpath("raiden_releases"))

        self.task_count = 0
        self.running_task_count = 0
        self.task_cache = {}
        self.task_state_callback = task_state_callback
        # Storage for arbitrary data tasks might need to persist
        self.task_storage = defaultdict(dict)

        scenario_name = scenario_file.stem
        self.base_path = data_path
        self.base_path.mkdir(exist_ok=True, parents=True)

        log.debug("Local seed", seed=self.local_seed)

        self.data_path = self.base_path.joinpath("scenarios", scenario_name)
        self.data_path.mkdir(exist_ok=True, parents=True)

        self.yaml = ScenarioYAML(scenario_file, self.data_path)
        log.debug("Data path", path=self.data_path)

        # Determining the run number requires :attr:`.data_path`
        self.run_number = self.determine_run_number()

        self.node_controller = NodeController(self, self.yaml.nodes)

        self.protocol = "http"

        self.gas_limit = GAS_LIMIT_FOR_TOKEN_CONTRACT_CALL * 2

        self.chain_name, chain_urls = self.select_chain(chain_urls)
        # Set CLI overrides.
        self.yaml.settings._cli_chain = self.chain_name
        self.yaml.settings._cli_rpc_address = chain_urls[0]
        self.eth_rpc_urls = chain_urls
        self.client = JSONRPCClient(
            Web3(HTTPProvider(chain_urls[0])),
            privkey=account.privkey,
            gas_price_strategy=self.yaml.settings.gas_price_strategy,
        )
        self.chain_id = int(self.client.web3.net.version)

        self.contract_manager = ContractManager(contracts_precompiled_path())

        balance = self.client.balance(account.address)
        if balance < OWN_ACCOUNT_BALANCE_MIN:
            raise ScenarioError(
                f"Insufficient balance ({balance / 10 ** 18} Eth) "
                f'in account {to_checksum_address(account.address)} on chain "{self.chain_name}"'
            )

        self.session = Session()
        if auth:
            self.session.auth = tuple(auth.split(":"))
        self.session.mount("http", TimeOutHTTPAdapter(timeout=self.yaml.settings.timeout))
        self.session.mount("https", TimeOutHTTPAdapter(timeout=self.yaml.settings.timeout))

        self.service_session = ServiceInterface(self.yaml.spaas)
        # Request an RPC Client instance ID from the RPC service and assign it to the runner.
        assign_rpc_instance_id(self, chain_urls[0], account.privkey, self.yaml.settings.gas_price)

        self.token = Token(self, data_path)
        self.udc = None

        self.token_network_address = None

        task_config = self.yaml.scenario.root_config
        task_class = self.yaml.scenario.root_class
        self.root_task = task_class(runner=self, config=task_config)

    def determine_run_number(self) -> int:
        """Determine the current run number.

        We check for a run number file, and use any number that is logged
        there after incrementing it.

        REFAC: Replace this with a property.
        """
        run_number = 0
        run_number_file = self.data_path.joinpath("run_number.txt")
        if run_number_file.exists():
            run_number = int(run_number_file.read_text()) + 1
        run_number_file.write_text(str(run_number))
        log.info("Run number", run_number=run_number)
        return run_number

    @property
    def local_seed(self) -> str:
        """Return a persistent random seed value.

        We need a unique seed per scenario player 'installation'.
        This is used in the node private key generation to prevent re-use of node keys between
        multiple users of the scenario player.

        The seed is stored in a file inside the ``.base_path``.
        """
        seed_file = self.base_path.joinpath("seed.txt")
        if not seed_file.exists():
            seed = encode_hex(bytes(random.randint(0, 255) for _ in range(20)))
            seed_file.write_text(seed)
        else:
            seed = seed_file.read_text().strip()
        return seed

    def select_chain(self, chain_urls: Dict[str, List[str]]) -> Tuple[str, List[str]]:
        """Select a chain and return its name and RPC URL.

        If the currently loaded scenario's designated chain is set to 'any',
        we randomly select a chain from the given `chain_urls`.
        Otherwise, we will return `ScenarioRunner.scenario.chain_name` and whatever value
        may be associated with this key in `chain_urls`.

        :raises ScenarioError:
            if ScenarioRunner.scenario.chain_name is not one of `('any', 'Any', 'ANY')`
            and it is not a key in `chain_urls`.
        """
        chain_name = self.yaml.settings.chain
        if chain_name in ("any", "Any", "ANY"):
            chain_name = random.choice(list(chain_urls.keys()))

        log.info("Using chain", chain=chain_name)
        try:
            return chain_name, chain_urls[chain_name]
        except KeyError:
            raise ScenarioError(
                f'The scenario requested chain "{chain_name}" for which no RPC-URL is known.'
            )

    def wait_for_token_network_discovery(self, node) -> ChecksumAddress:
        """Check for token network discovery with the given `node`.

        By default exit the wait if the token has not been discovered after `n` seconds,
        where `n` is the value of :attr:`.timeout`.

        :raises TokenNetworkDiscoveryTimeout:
            If we waited a set time for the token network to be discovered, but it wasn't.
        """
        log.info("Waiting till new network is found by nodes")
        node_endpoint = API_URL_TOKEN_NETWORK_ADDRESS.format(
            protocol=self.protocol, target_host=node, token_address=self.token.address
        )

        started = time.monotonic()
        elapsed = 0
        while elapsed < self.yaml.settings.timeout:
            try:
                resp = self.session.get(node_endpoint)
                resp.raise_for_status()

            except HTTPError as e:
                # We explicitly handle 404 Not Found responses only - anything else is none
                # of our business.
                if e.response.status_code != 404:
                    raise

                # Wait before continuing, no sense in spamming the node.
                gevent.sleep(1)

                # Update our elapsed time tracker.
                elapsed = time.monotonic() - started
                continue

            else:
                # The node appears to have discovered our token network.
                data = resp.json()

                if not is_checksum_address(data):
                    # Something's amiss about this response. Notify a human.
                    raise TypeError(f"Unexpected response type from API: {data!r}")

                return data

        # We could not assert that our token network was registered within an
        # acceptable time frame.
        raise TokenNetworkDiscoveryTimeout

    def ensure_token_network_discovery(self) -> ChecksumAddress:
        """Ensure that all our nodes have discovered the token network."""
        discovered = None
        for node in self.node_controller:
            discovered = self.wait_for_token_network_discovery(node.base_url)
            log.info("Token Network Discovery", node=node._index, network=discovered)
        return discovered

    def run_scenario(self):
        mint_gas = GAS_LIMIT_FOR_TOKEN_CONTRACT_CALL * 2

        fund_tx, node_starter, node_addresses, node_count = self._initialize_nodes()

        ud_token_tx, udc_ctr, should_deposit_ud_token = self._initialize_udc(
            gas_limit=mint_gas, node_count=node_count
        )

        mint_tx = self._initialize_scenario_token(
            node_addresses=node_addresses,
            udc_ctr=udc_ctr,
            should_deposit_ud_token=should_deposit_ud_token,
            gas_limit=mint_gas,
        )

        wait_for_txs(self.client, fund_tx | ud_token_tx | mint_tx)

        if node_starter is not None:
            log.debug("Waiting for nodes to finish starting")
            node_starter.get(block=True)

        first_node = self.get_node_baseurl(0)

        registered_tokens = set(
            self.session.get(
                API_URL_TOKENS.format(protocol=self.protocol, target_host=first_node)
            ).json()
        )
        if self.token.checksum_address not in registered_tokens:
            for _ in range(5):
                code, msg = self.register_token(self.token.checksum_address, first_node)
                if 199 < code < 300:
                    break
                gevent.sleep(1)
            else:
                log.error("Couldn't register token with network", code=code, message=msg)
                raise TokenRegistrationError(msg)

        self.token_network_address = self.ensure_token_network_discovery()
        log.info(
            "Token Network Discovery Completed", token_network_address=self.token_network_address
        )

        # Start root task
        root_task_greenlet = gevent.spawn(self.root_task)
        greenlets = {root_task_greenlet}
        greenlets.add(self.node_controller.start_node_monitor())
        try:
            gevent.joinall(greenlets, raise_error=True)
        except BaseException:
            if not root_task_greenlet.dead:
                # Make sure we kill the tasks if a node dies
                root_task_greenlet.kill()
            raise

    def _initialize_scenario_token(
        self,
        node_addresses: Set[ChecksumAddress],
        udc_ctr: Optional[ContractProxy],
        should_deposit_ud_token: bool,
        gas_limit: int,
    ) -> Set[TransactionHash]:
        """Create or reuse an existing token, and mint the token for every
        `node_addresses`.
        """
        self.token.init()
        mint_tx = set()
        for address in node_addresses:
            tx = self.token.mint(address)
            if tx:
                mint_tx.add(tx)

            if not should_deposit_ud_token:
                continue
            deposit_tx = self.udc.deposit(address)
            if deposit_tx:
                mint_tx.add(deposit_tx)

        return mint_tx

    def _initialize_udc(
        self, gas_limit: int, node_count: int
    ) -> Tuple[Set[TransactionHash], Optional[ContractProxy], bool]:
        our_address = to_checksum_address(self.client.address)
        udc_settings = self.yaml.settings.services.udc
        udc_enabled = udc_settings.enable

        ud_token_tx = set()

        if not udc_enabled:
            return ud_token_tx, None, False

        udc_ctr, ud_token_ctr = get_udc_and_token(self)

        ud_token_address = to_checksum_address(ud_token_ctr.contract_address)
        udc_address = to_checksum_address(udc_ctr.contract_address)

        log.info("UDC enabled", contract_address=udc_address, token_address=ud_token_address)

        self.udc = UserDepositContract(self, udc_ctr, ud_token_ctr)

        should_deposit_ud_token = udc_enabled and udc_settings.token.deposit
        allowance_tx, required_allowance = self.udc.update_allowance()
        if allowance_tx:
            ud_token_tx.add(allowance_tx)
        if should_deposit_ud_token:

            tx = self.udc.mint(
                our_address,
                required_balance=required_allowance,
                max_fund_amount=required_allowance * 2,
            )
            if tx:
                ud_token_tx.add(tx)

        return ud_token_tx, udc_ctr, should_deposit_ud_token

    def _initialize_nodes(
        self
    ) -> Tuple[Set[TransactionHash], gevent.Greenlet, Set[ChecksumAddress], int]:
        """This methods starts all the Raiden nodes and makes sure that each
        account has at least `NODE_ACCOUNT_BALANCE_MIN`.
        """
        fund_tx = set()

        self.node_controller.initialize_nodes()
        node_addresses = self.node_controller.addresses
        node_count = len(self.node_controller)
        balance_per_node = {address: self.client.balance(address) for address in node_addresses}
        low_balances = {
            address: balance
            for address, balance in balance_per_node.items()
            if balance < NODE_ACCOUNT_BALANCE_MIN
        }
        log.debug("Node eth balances", balances=balance_per_node, low_balances=low_balances)
        if low_balances:
            log.info("Funding nodes", nodes=low_balances.keys())
            fund_tx = set()
            for address, balance in low_balances.items():
                params = {
                    "client_id": self.yaml.spaas.rpc.client_id,
                    "to": address,
                    "value": NODE_ACCOUNT_BALANCE_FUND - balance,
                    "startgas": 21_000,
                }
                resp = self.service_session.post("spaas://rpc/transactions", json=params)
                tx_hash = resp.json()["tx_hash"]
                fund_tx.add(tx_hash)

        node_starter = self.node_controller.start(wait=False)

        return fund_tx, node_starter, node_addresses, node_count

    def task_state_changed(self, task: "Task", state: "TaskState"):
        if self.task_state_callback:
            self.task_state_callback(self, task, state)

    def register_token(self, token_address, node):
        # TODO: Move this to :class:`scenario_player.utils.token.Token`.
        try:
            base_url = API_URL_TOKENS.format(protocol=self.protocol, target_host=node)
            url = "{}/{}".format(base_url, token_address)
            log.info("Registering token with network", url=url)
            resp = self.session.put(url)
            code = resp.status_code
            msg = resp.text
        except RequestException as ex:
            code = -1
            msg = str(ex)
        return code, msg

    @staticmethod
    def _spawn_and_wait(objects, callback):
        tasks = {obj: gevent.spawn(callback, obj) for obj in objects}
        gevent.joinall(set(tasks.values()))
        return {obj: task.get() for obj, task in tasks.items()}

    def get_node_address(self, index):
        return self.node_controller[index].address

    def get_node_baseurl(self, index):
        return self.node_controller[index].base_url

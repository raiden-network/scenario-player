import random
import time
from collections import defaultdict
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Dict, List, Optional, Set, Tuple, cast

import gevent
import requests
import structlog
from eth_typing import ChecksumAddress
from eth_utils import encode_hex, is_checksum_address, to_checksum_address, to_hex
from gevent import Greenlet
from gevent.event import Event
from gevent.pool import Pool
from raiden_contracts.constants import (
    CHAINNAME_TO_ID,
    CONTRACT_CUSTOM_TOKEN,
    CONTRACT_TOKEN_NETWORK_REGISTRY,
)
from raiden_contracts.contract_manager import DeployedContracts, get_contracts_deployment_info
from raiden_contracts.utils.type_aliases import TokenAmount
from requests import HTTPError, Session
from web3 import HTTPProvider, Web3

from raiden.accounts import Account
from raiden.constants import UINT256_MAX
from raiden.network.proxies.custom_token import CustomToken
from raiden.network.proxies.proxy_manager import ProxyManager
from raiden.network.proxies.token_network_registry import TokenNetworkRegistry
from raiden.network.proxies.user_deposit import UserDeposit
from raiden.network.rpc.client import JSONRPCClient
from raiden.network.rpc.middleware import faster_gas_price_strategy
from raiden.settings import DEFAULT_NUMBER_OF_BLOCK_CONFIRMATIONS, RAIDEN_CONTRACT_VERSION
from raiden.utils.formatting import to_canonical_address
from raiden.utils.nursery import Janitor
from raiden.utils.typing import (
    Address,
    ChainID,
    TokenAddress,
    TokenNetworkAddress,
    TokenNetworkRegistryAddress,
)
from scenario_player.constants import (
    API_URL_TOKEN_NETWORK_ADDRESS,
    MAX_RAIDEN_STARTUP_TIME,
    NODE_ACCOUNT_BALANCE_FUND,
    NODE_ACCOUNT_BALANCE_MIN,
    OWN_ACCOUNT_BALANCE_MIN,
    RUN_NUMBER_FILENAME,
)
from scenario_player.definition import ScenarioDefinition
from scenario_player.exceptions import ScenarioError, TokenNetworkDiscoveryTimeout
from scenario_player.node_support import NodeController, NodeRunner
from scenario_player.utils import TimeOutHTTPAdapter
from scenario_player.utils.configuration.settings import (
    EnvironmentConfig,
    SettingsConfig,
    UDCSettingsConfig,
)
from scenario_player.utils.contracts import (
    get_proxy_manager,
    get_udc_and_corresponding_token_from_dependencies,
)
from scenario_player.utils.token import (
    TokenDetails,
    eth_maybe_transfer,
    load_token_configuration_from_file,
    save_token_configuration_to_file,
    token_maybe_mint,
    userdeposit_maybe_deposit,
    userdeposit_maybe_increase_allowance,
)

if TYPE_CHECKING:
    from scenario_player.tasks.base import Task, TaskState

log = structlog.get_logger(__name__)


# The `mint` function checks for overflow of the total supply. Here we
# have a large enough number for both scenario runs and the scenario
# orchestration account capacity.
NUMBER_OF_RUNS_BEFORE_OVERFLOW = 2 ** 64
ORCHESTRATION_MAXIMUM_BALANCE = UINT256_MAX // NUMBER_OF_RUNS_BEFORE_OVERFLOW


def is_udc_enabled(udc_settings: UDCSettingsConfig):
    should_deposit_ud_token = udc_settings.token.deposit
    return udc_settings.enable and should_deposit_ud_token


def wait_for_nodes_to_be_ready(node_runners: List[NodeRunner], session: Session):
    with gevent.Timeout(MAX_RAIDEN_STARTUP_TIME):
        for node_runner in node_runners:
            url = f"http://{node_runner.base_url}/api/v1/status"
            while True:
                try:
                    if session.get(url).json()["status"] == "ready":
                        break
                except (requests.exceptions.RequestException, ValueError, KeyError):
                    pass
                gevent.sleep(1.0)


def get_token_network_registry_from_dependencies(
    settings: SettingsConfig,
    proxy_manager: ProxyManager,
    smoketest_deployment_data: DeployedContracts = None,
) -> TokenNetworkRegistry:
    """ Return contract proxies for the UserDepositContract and associated token.

    This will return a proxy to the `UserDeposit` contract as determined by the
    **local** Raiden dependency.
    """
    chain_id = settings.chain_id
    assert chain_id, "Missing configuration, either set udc_address or the chain_id"

    if chain_id != CHAINNAME_TO_ID["smoketest"]:
        contracts = get_contracts_deployment_info(chain_id, version=RAIDEN_CONTRACT_VERSION)
    else:
        contracts = smoketest_deployment_data

    msg = f"invalid chain_id, {chain_id} is not available for version {RAIDEN_CONTRACT_VERSION}"
    assert contracts, msg

    token_network_address = contracts["contracts"][CONTRACT_TOKEN_NETWORK_REGISTRY]["address"]

    token_network_proxy = proxy_manager.token_network_registry(
        TokenNetworkRegistryAddress(to_canonical_address(token_network_address)), "latest"
    )
    return token_network_proxy


def determine_run_number(scenario_dir: Path) -> int:
    """ Determine the current run number.

    We check for a run number file, and use any number that is logged there
    after incrementing it.
    """
    # TODO: Use advisory file locks to avoid concurrent read/writes on the
    # run_number_file. Otherwise this can lead to very hard to debug races.
    run_number_file = scenario_dir.joinpath(RUN_NUMBER_FILENAME)

    if run_number_file.exists():
        run_number = int(run_number_file.read_text()) + 1
    else:
        run_number = 0

    run_number_file.write_text(str(run_number))

    return run_number


def make_session(auth: str, settings: SettingsConfig) -> Session:
    session = Session()
    if auth:
        session.auth = cast(Tuple[str, str], tuple(auth.split(":")))
    session.mount("http", TimeOutHTTPAdapter(timeout=settings.timeout))
    session.mount("https", TimeOutHTTPAdapter(timeout=settings.timeout))

    return session


def wait_for_token_network_discovery(
    node_endpoint: str, settings: SettingsConfig, session: Session
) -> ChecksumAddress:
    """Check for token network discovery with the given `node`.

    By default exit the wait if the token has not been discovered after `n` seconds,
    where `n` is the value of :attr:`.timeout`.

    :raises TokenNetworkDiscoveryTimeout:
        If we waited a set time for the token network to be discovered, but it wasn't.
    """
    started = time.monotonic()
    elapsed = 0.0
    while elapsed < settings.timeout:
        try:
            resp = session.get(node_endpoint)
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

            return ChecksumAddress(data)

    # We could not assert that our token network was registered within an
    # acceptable time frame.
    raise TokenNetworkDiscoveryTimeout


def maybe_create_token_network(
    token_network_proxy: TokenNetworkRegistry, token_proxy: CustomToken
) -> TokenNetworkAddress:
    """ Make sure the token is registered with the node's network registry. """
    block_identifier = token_network_proxy.rpc_client.get_confirmed_blockhash()
    token_address = token_proxy.address

    token_network_address = token_network_proxy.get_token_network(
        token_address=token_address, block_identifier=block_identifier
    )

    if token_network_address is None:
        return token_network_proxy.add_token(
            token_address=token_address,
            channel_participant_deposit_limit=TokenAmount(UINT256_MAX),
            token_network_deposit_limit=TokenAmount(UINT256_MAX),
            given_block_identifier=block_identifier,
        )
    else:
        return token_network_address


class ScenarioRunner:
    def __init__(
        self,
        account: Account,
        auth: str,
        data_path: Path,
        scenario_file: Path,
        environment: EnvironmentConfig,
        success: Event,
        task_state_callback: Optional[
            Callable[["ScenarioRunner", "Task", "TaskState"], None]
        ] = None,
        smoketest_deployment_data: DeployedContracts = None,
        delete_snapshots: bool = False,
    ) -> None:
        from scenario_player.node_support import RaidenReleaseKeeper

        self.auth = auth
        self.success = success

        self.smoketest_deployment_data = smoketest_deployment_data
        self.delete_snapshots = delete_snapshots

        self.release_keeper = RaidenReleaseKeeper(data_path.joinpath("raiden_releases"))
        self.data_path = data_path
        self.environment = environment

        self.task_count = 0
        self.running_task_count = 0
        self.task_cache: Dict[str, Task] = {}
        self.task_state_callback = task_state_callback
        # Storage for arbitrary data tasks might need to persist
        self.task_storage: Dict[str, dict] = defaultdict(dict)

        self.definition = ScenarioDefinition(scenario_file, data_path, self.environment)

        log.debug("Local seed", seed=self.local_seed)

        self.run_number = determine_run_number(self.definition.scenario_dir)

        log.info("Run number", run_number=self.run_number)

        self.protocol = "http"
        web3 = Web3(HTTPProvider(environment.eth_rpc_endpoints[0]))
        self.chain_id = ChainID(web3.eth.chainId)
        self.definition.settings.eth_rpc_endpoint_iterator = environment.eth_rpc_endpoint_iterator
        self.definition.settings.chain_id = self.chain_id

        assert account.privkey, "Account not unlockable"
        self.client = JSONRPCClient(
            web3=web3,
            privkey=account.privkey,
            gas_price_strategy=faster_gas_price_strategy,
            block_num_confirmations=DEFAULT_NUMBER_OF_BLOCK_CONFIRMATIONS,
        )

        assert account.address, "Account not loaded"
        balance = self.client.balance(account.address)
        if balance < OWN_ACCOUNT_BALANCE_MIN:
            raise ScenarioError(
                f"Insufficient balance ({balance / 10 ** 18} Eth) "
                f"in account {to_checksum_address(account.address)} "
                f'on chain "{self.definition.settings.chain_id}"'
                f" - it needs additional {(OWN_ACCOUNT_BALANCE_MIN - balance) / 10 ** 18} Eth ("
                f"that is {OWN_ACCOUNT_BALANCE_MIN - balance} Wei)."
            )

        self.session = make_session(auth, self.definition.settings)

        self.node_controller = NodeController(
            self, self.definition.nodes, delete_snapshots=self.delete_snapshots
        )
        task_config = self.definition.scenario.root_config
        task_class = self.definition.scenario.root_class
        self.root_task = task_class(runner=self, config=task_config)

    @property
    def local_seed(self) -> str:
        """Return a persistent random seed value.

        We need a unique seed per scenario player 'installation'.
        This is used in the node private key generation to prevent re-use of node keys between
        multiple users of the scenario player.

        The seed is stored in a file inside the ``.definition.settings.sp_root_dir``.
        """
        assert self.definition.settings.sp_root_dir
        seed_file = self.definition.settings.sp_root_dir.joinpath("seed.txt")
        if not seed_file.exists():
            seed = str(encode_hex(bytes(random.randint(0, 255) for _ in range(20))))
            seed_file.write_text(seed)
        else:
            seed = seed_file.read_text().strip()
        return seed

    def ensure_token_network_discovery(
        self, token: CustomToken, token_network_addresses: TokenNetworkAddress
    ) -> None:
        """Ensure that all our nodes have discovered the same token network."""
        for node in self.node_controller:  # type: ignore
            node_endpoint = API_URL_TOKEN_NETWORK_ADDRESS.format(
                protocol=self.protocol,
                target_host=node.base_url,
                token_address=to_checksum_address(token.address),
            )
            address = wait_for_token_network_discovery(
                node_endpoint, self.definition.settings, self.session
            )
            if to_canonical_address(address) != Address(token_network_addresses):
                raise RuntimeError(
                    f"Nodes diverged on the token network address, there should be "
                    f"exactly one token network available for all nodes. Current "
                    f"values : {to_hex(token_network_addresses)}"
                )

    def run_scenario(self) -> None:
        with Janitor() as nursery:
            self.node_controller.set_nursery(nursery)
            self.node_controller.initialize_nodes()

            try:
                for node_runner in self.node_controller._node_runners:
                    node_runner.start()
            except Exception:
                log.error("failed to start", exc_info=True)
                raise

            node_addresses = self.node_controller.addresses

            scenario = nursery.spawn_under_watch(
                self.setup_environment_and_run_main_task, node_addresses
            )
            scenario.name = "orchestration"

            # Wait for either a crash in one of the Raiden nodes or for the
            # scenario to exit (successfully or not).
            greenlets = {scenario}
            gevent.joinall(greenlets, raise_error=True, count=1)
        self.success.set()

    def setup_environment_and_run_main_task(self, node_addresses: Set[ChecksumAddress]) -> None:
        """ This will first make sure the on-chain state is setup properly, and
        then execute the scenario.

        The on-chain state consists of:

        - Deployment of the test CustomToken
        - For each of the Raiden nodes, make sure they have enough:

            - Ether to pay for the transactions.
            - Utility token balances in the user deposit smart contract.
            - Tokens to be used with the test token network.
        """
        block_execution_started = self.client.block_number()

        settings = self.definition.settings
        udc_settings = settings.services.udc

        smoketesting = False
        if self.chain_id != CHAINNAME_TO_ID["smoketest"]:
            deploy = get_contracts_deployment_info(self.chain_id, RAIDEN_CONTRACT_VERSION)
        else:
            smoketesting = True
            deploy = self.smoketest_deployment_data

        msg = "There is no deployment details for the given chain_id and contracts version pair"
        assert deploy, msg

        proxy_manager = get_proxy_manager(self.client, deploy)

        # Tracking pool to synchronize on all concurrent transactions
        pool = Pool()

        log.debug("Funding Raiden node's accounts with ether")
        self.setup_raiden_nodes_ether_balances(pool, node_addresses)

        if is_udc_enabled(udc_settings):
            (
                userdeposit_proxy,
                user_token_proxy,
            ) = get_udc_and_corresponding_token_from_dependencies(
                udc_address=udc_settings.address,
                chain_id=settings.chain_id,
                proxy_manager=proxy_manager,
            )

            log.debug("Minting utility tokens and /scheduling/ transfers to the nodes")
            mint_greenlets = self.setup_mint_user_deposit_tokens_for_distribution(
                pool, userdeposit_proxy, user_token_proxy, node_addresses
            )
            self.setup_raiden_nodes_with_sufficient_user_deposit_balances(
                pool, userdeposit_proxy, node_addresses, mint_greenlets
            )

        # This is a blocking call. If the token has to be deployed it will
        # block until mined and confirmed, since that is a requirement for the
        # following setup calls.
        token_proxy = self.setup_token_contract_for_token_network(proxy_manager)
        if smoketesting:
            token_network_registry_proxy = get_token_network_registry_from_dependencies(
                settings=settings, proxy_manager=proxy_manager, smoketest_deployment_data=deploy
            )
        else:
            token_network_registry_proxy = get_token_network_registry_from_dependencies(
                settings=settings, proxy_manager=proxy_manager
            )

        self.setup_raiden_token_balances(pool, token_proxy, node_addresses)

        # Wait for all the transactions
        # - Move ether from the orcheastration account (the scenario player),
        # to the raiden nodes.
        # - Mint enough utility tokens (user deposit tokens) for the
        # orchestration account to transfer for the nodes.
        # - Mint network tokens for the nodes to use in the scenarion.
        # - Deposit utility tokens for the raiden nodes in the user deposit
        # contract.
        log.debug("Waiting for funding transactions to be mined")
        pool.join(raise_error=True)

        log.debug("Registering token to create the network")
        token_network_address = maybe_create_token_network(
            token_network_registry_proxy, token_proxy
        )

        log.debug("Waiting for the REST APIs")
        wait_for_nodes_to_be_ready(self.node_controller._node_runners, self.session)

        log.info("Making sure all nodes have the same token network")
        self.ensure_token_network_discovery(token_proxy, token_network_address)

        log.info(
            "Setup done, running scenario",
            token_network_address=to_checksum_address(token_network_address),
        )

        # Expose attributes used by the tasks
        self.token = token_proxy
        self.contract_manager = proxy_manager.contract_manager
        self.token_network_address = to_checksum_address(token_network_address)
        self.block_execution_started = block_execution_started

        self.root_task()

    def setup_raiden_nodes_ether_balances(
        self, pool: Pool, node_addresses: Set[ChecksumAddress]
    ) -> Set[Greenlet]:
        """ Makes sure every Raiden node has at least `NODE_ACCOUNT_BALANCE_MIN`. """

        greenlets: Set[Greenlet] = set()
        for address in node_addresses:
            g = pool.spawn(
                eth_maybe_transfer,
                orchestration_client=self.client,
                target=to_canonical_address(address),
                minimum_balance=NODE_ACCOUNT_BALANCE_MIN,
                maximum_balance=NODE_ACCOUNT_BALANCE_FUND,
            )
            greenlets.add(g)

        return greenlets

    def setup_mint_user_deposit_tokens_for_distribution(
        self,
        pool: Pool,
        userdeposit_proxy: UserDeposit,
        token_proxy: CustomToken,
        node_addresses: Set[ChecksumAddress],
    ) -> Set[Greenlet]:
        """ Ensures the scenario player account has enough tokens and allowance
        to fund the Raiden nodes.
        """
        settings = self.definition.settings
        udc_settings = settings.services.udc
        balance_per_node = settings.services.udc.token.balance_per_node

        msg = "udc is not enabled, this function should not be called"
        assert is_udc_enabled(udc_settings), msg

        node_count = len(node_addresses)
        required_allowance = balance_per_node * node_count

        allowance_greenlet = pool.spawn(
            userdeposit_maybe_increase_allowance,
            token_proxy=token_proxy,
            userdeposit_proxy=userdeposit_proxy,
            orchestrator_address=self.client.address,
            minimum_allowance=required_allowance,
            maximum_allowance=UINT256_MAX,
        )

        mint_greenlet = pool.spawn(
            token_maybe_mint,
            token_proxy=token_proxy,
            target_address=to_checksum_address(self.client.address),
            minimum_balance=required_allowance,
            maximum_balance=ORCHESTRATION_MAXIMUM_BALANCE,
        )

        return {allowance_greenlet, mint_greenlet}

    def setup_raiden_token_balances(
        self, pool: Pool, token_proxy: CustomToken, node_addresses: Set[ChecksumAddress]
    ) -> Set[Greenlet]:
        """Mint the necessary amount of tokens from `token_proxy` for every `node_addresses`.

        This will use the scenario player's account, therefore it doesn't have
        to wait for the ether transfers to finish.
        """
        token_min_amount = self.definition.token.min_balance
        token_max_amount = self.definition.token.max_funding

        greenlets: Set[Greenlet] = set()
        for address in node_addresses:
            g = pool.spawn(
                token_maybe_mint,
                token_proxy=token_proxy,
                target_address=address,
                minimum_balance=token_min_amount,
                maximum_balance=token_max_amount,
            )
            greenlets.add(g)

        return greenlets

    def setup_raiden_nodes_with_sufficient_user_deposit_balances(
        self,
        pool: Pool,
        userdeposit_proxy: UserDeposit,
        node_addresses: Set[ChecksumAddress],
        mint_greenlets: Set[Greenlet],
    ) -> Set[Greenlet]:
        """ Makes sure every Raiden node's account has enough tokens in the
        user deposit contract.

        For these transfers to work, the approve and mint transacations have to
        be mined and confirmed. This is necessary because otherwise the gas
        estimation of the deposits fail.
        """
        msg = "udc is not enabled, this function should not be called"
        assert is_udc_enabled(self.definition.settings.services.udc), msg

        minimum_effective_deposit = self.definition.settings.services.udc.token.balance_per_node
        maximum_funding = self.definition.settings.services.udc.token.max_funding

        log.debug("Depositing utility tokens for the nodes")
        greenlets: Set[Greenlet] = set()
        for address in node_addresses:
            g = pool.spawn(
                userdeposit_maybe_deposit,
                userdeposit_proxy=userdeposit_proxy,
                mint_greenlets=mint_greenlets,
                target_address=to_canonical_address(address),
                minimum_effective_deposit=minimum_effective_deposit,
                maximum_funding=maximum_funding,
            )
            greenlets.add(g)

        return greenlets

    def setup_token_contract_for_token_network(self, proxy_manager: ProxyManager) -> CustomToken:
        """ Ensure there is a deployed token contract and return a `CustomToken`
        proxy to it. This token will be used for the scenario's token network.

        This will either:

        - Use the token from the address provided in the scenario
          configuration.
        - Use a previously deployed token, with the details loaded from the
          disk.
        - Deploy a new token if neither of the above options is used.
        """
        token_definition = self.definition.token
        reuse_token_from_file = token_definition.can_reuse_token

        if token_definition.address:
            token_address = to_canonical_address(token_definition.address)
        elif reuse_token_from_file:
            token_details = load_token_configuration_from_file(token_definition.token_file)
            token_address = to_canonical_address(token_details["address"])
        else:
            contract_data = proxy_manager.contract_manager.get_contract(CONTRACT_CUSTOM_TOKEN)
            contract, receipt = self.client.deploy_single_contract(
                contract_name=CONTRACT_CUSTOM_TOKEN,
                contract=contract_data,
                constructor_parameters=(
                    ORCHESTRATION_MAXIMUM_BALANCE,
                    token_definition.decimals,
                    token_definition.name,
                    token_definition.symbol,
                ),
            )
            token_address = to_canonical_address(contract.address)

            if token_definition.should_reuse_token:
                details = TokenDetails(
                    {
                        "name": token_definition.name,
                        "address": to_checksum_address(token_address),
                        "block": receipt["blockNumber"],
                    }
                )
                save_token_configuration_to_file(token_definition.token_file, details)

        return proxy_manager.custom_token(TokenAddress(token_address), "latest")

    def task_state_changed(self, task: "Task", state: "TaskState"):
        if self.task_state_callback:
            self.task_state_callback(self, task, state)

    def get_node_address(self, index):
        return self.node_controller[index].address

    def get_node_baseurl(self, index):
        return self.node_controller[index].base_url

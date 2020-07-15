import json
import pathlib
import time
from dataclasses import dataclass
from itertools import chain as iter_chain
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import structlog
from eth_keyfile import decode_keyfile_json
from eth_utils import to_canonical_address, to_checksum_address
from gevent.pool import Pool
from raiden_contracts.constants import CONTRACT_TOKEN_NETWORK_REGISTRY, ChannelEvent
from raiden_contracts.contract_manager import (
    ContractManager,
    DeployedContracts,
    get_contracts_deployment_info,
)
from web3 import Web3

from raiden.accounts import Account
from raiden.blockchain.events import BlockchainEvents, token_network_events
from raiden.constants import BLOCK_ID_LATEST
from raiden.exceptions import InsufficientEth
from raiden.messages.abstract import cached_property
from raiden.network.proxies.custom_token import CustomToken
from raiden.network.proxies.proxy_manager import ProxyManager
from raiden.network.proxies.token_network import TokenNetwork
from raiden.network.rpc.client import EthTransfer, JSONRPCClient
from raiden.network.rpc.middleware import faster_gas_price_strategy
from raiden.settings import (
    DEFAULT_NUMBER_OF_BLOCK_CONFIRMATIONS,
    RAIDEN_CONTRACT_VERSION,
    BlockBatchSizeConfig,
)
from raiden.transfer.identifiers import CanonicalIdentifier
from raiden.utils.packing import pack_withdraw
from raiden.utils.signer import LocalSigner
from raiden.utils.typing import (
    Address,
    BlockExpiration,
    BlockIdentifier,
    BlockNumber,
    ChainID,
    ChannelID,
    ChecksumAddress,
    PrivateKey,
    TokenAddress,
    TokenAmount,
    TokenNetworkAddress,
    TokenNetworkRegistryAddress,
    WithdrawAmount,
)
from scenario_player.utils.contracts import (
    get_proxy_manager,
    get_udc_and_corresponding_token_from_dependencies,
)
from scenario_player.utils.legacy import wait_for_txs

log = structlog.get_logger(__name__)

VALUE_TX_GAS_COST = 21_000


@dataclass
class ReclamationCandidate:
    address: ChecksumAddress
    keyfile_content: dict
    node_dir: pathlib.Path

    @cached_property
    def privkey(self):
        return decode_keyfile_json(self.keyfile_content, b"")

    def get_client(self, web3: Web3) -> JSONRPCClient:
        if not hasattr(self, "_client"):
            self._web3 = web3
            self._client = JSONRPCClient(
                web3=web3, privkey=self.privkey, gas_price_strategy=faster_gas_price_strategy
            )
        else:
            assert web3 == self._web3
        return self._client

    def get_proxy_manager(self, web3: Web3, deploy: DeployedContracts) -> ProxyManager:
        if not hasattr(self, "_proxy_manager"):
            self._deploy = deploy
            self._proxy_manager = get_proxy_manager(self.get_client(web3), deploy)
        else:
            assert deploy == self._deploy
        return self._proxy_manager


def get_reclamation_candidates(
    data_path: pathlib.Path, min_age_hours: int
) -> List[ReclamationCandidate]:
    candidates: List[ReclamationCandidate] = []
    for node_dir in iter_chain(data_path.glob("**/node_???"), data_path.glob("**/node_*_???")):
        if (node_dir / "reclaimed").exists():
            continue

        last_run = next(
            iter(
                sorted(
                    list(node_dir.glob("run-*.log*")),
                    key=lambda p: p.stat().st_mtime,
                    reverse=True,
                )
            ),
            None,
        )
        # If there is no last run assume we can reclaim
        if last_run:
            age_hours = (time.time() - last_run.stat().st_mtime) / 3600
            if age_hours < min_age_hours:
                scenario_name: Path = Path(node_dir.parent.name)
                log.debug(
                    "Skipping too recent node",
                    scenario_name=scenario_name,
                    node=node_dir.name,
                    age_hours=age_hours,
                )
                continue
        for keyfile in node_dir.glob("keys/*"):
            keyfile_content = json.loads(keyfile.read_text())
            address = keyfile_content.get("address")
            if address:
                candidates.append(
                    ReclamationCandidate(
                        address=to_checksum_address(address),
                        node_dir=node_dir,
                        keyfile_content=keyfile_content,
                    )
                )
    return candidates


def withdraw_from_udc(
    reclamation_candidates: List[ReclamationCandidate],
    contract_manager: ContractManager,
    account: Account,
    web3: Web3,
):
    chain_id = ChainID(web3.eth.chainId)
    deploy = get_contracts_deployment_info(chain_id, RAIDEN_CONTRACT_VERSION)
    assert deploy

    planned_withdraws: Dict[ChecksumAddress, Tuple[BlockNumber, TokenAmount]] = dict()

    log.info("Checking chain for deposits in UserDeposit contact")
    for node in reclamation_candidates:
        (userdeposit_proxy, _) = get_udc_and_corresponding_token_from_dependencies(
            chain_id=chain_id, proxy_manager=node.get_proxy_manager(web3, deploy)
        )

        balance = userdeposit_proxy.get_total_deposit(to_canonical_address(node.address), "latest")
        log.debug("UDC balance", balance=balance, address=node.address)
        if balance > 0:
            drain_amount = TokenAmount(balance)
            log.info(
                "Planning withdraw",
                from_address=node.address,
                amount=drain_amount.__format__(",d"),
            )
            try:
                ready_at_block = userdeposit_proxy.plan_withdraw(drain_amount, "latest")
            except InsufficientEth:
                log.warning("Not sufficient eth in node wallet to withdraw", address=node.address)
                continue
            planned_withdraws[node.address] = ready_at_block, drain_amount

    if not planned_withdraws:
        return

    log.info(
        "Withdraws successfully planned, waiting until withdraws are ready",
        planned_withdraws=planned_withdraws,
    )

    reclaim_amount = 0
    for address, (ready_at_block, amount) in planned_withdraws.items():
        candidate = [c for c in reclamation_candidates if c.address == address][0]
        proxy_manager = candidate.get_proxy_manager(web3, deploy)
        (userdeposit_proxy, _) = get_udc_and_corresponding_token_from_dependencies(
            chain_id=chain_id, proxy_manager=proxy_manager
        )
        # FIXME: Something is off with the block numbers, adding 20 to work around.
        #        See https://github.com/raiden-network/raiden/pull/6091/files#r412234516
        proxy_manager.client.wait_until_block(BlockNumber(ready_at_block + 20), retry_timeout=10)

        log.info("Withdraw", user_address=address, amount=amount.__format__(",d"))
        reclaim_amount += amount
        userdeposit_proxy.withdraw(amount, "latest")

    log.info(
        "All UDC withdraws finished, now claim the resulting tokens!",
        withdraw_total=reclaim_amount.__format__(",d"),
    )

    reclaim_erc20(
        reclamation_candidates,
        userdeposit_proxy.token_address("latest"),
        contract_manager,
        account,
        web3,
    )


def reclaim_erc20(
    reclamation_candidates: List[ReclamationCandidate],
    token_address: TokenAddress,
    contract_manager: ContractManager,
    account: Account,
    web3: Web3,
):
    reclaim_amount = 0

    log.info("Checking chain for claimable tokens", token_address=token_address)
    for node in reclamation_candidates:
        client = node.get_client(web3)
        confirmed_block_hash = client.get_confirmed_blockhash()
        token = CustomToken(client, token_address, contract_manager, confirmed_block_hash)

        balance = token.balance_of(to_canonical_address(node.address))
        log.debug(
            "balance",
            token=to_checksum_address(token_address),
            balance=balance,
            address=node.address,
        )
        if balance > 0:
            drain_amount = balance
            log.info(
                "Reclaiming tokens",
                from_address=node.address,
                amount=drain_amount.__format__(",d"),
            )
            reclaim_amount += drain_amount
            assert account.address
            try:
                token.transfer(account.address, TokenAmount(drain_amount))
            except InsufficientEth:
                log.warning(
                    "Not sufficient eth in node wallet to reclaim",
                    address=node.address,
                    token_address=token_address,
                )
                continue

    if reclaim_amount:
        log.info(
            "Reclaimed",
            reclaim_amount=reclaim_amount.__format__(",d"),
            token_address=to_checksum_address(token.address),
        )


def reclaim_eth(reclamation_candidates: List[ReclamationCandidate], account: Account, web3: Web3):
    txs = []
    reclaim_amount = 0
    gas_price = web3.eth.gasPrice
    reclaim_tx_cost = gas_price * VALUE_TX_GAS_COST

    log.info("Checking chain for claimable ETH")
    for node in reclamation_candidates:
        balance = web3.eth.getBalance(node.address)
        if balance > reclaim_tx_cost:
            drain_amount = balance - reclaim_tx_cost
            log.info("Reclaiming", from_address=node.address, amount=drain_amount.__format__(",d"))
            reclaim_amount += drain_amount
            assert account.address
            txs.append(
                node.get_client(web3).transact(
                    EthTransfer(
                        to_address=account.address, value=drain_amount, gas_price=gas_price
                    )
                )
            )
        (node.node_dir / "reclaimed").touch()

    wait_for_txs(web3, txs, 1000)
    log.info("Reclaimed", reclaim_amount=reclaim_amount.__format__(",d"))


def _get_all_token_network_events(
    contract_manager: ContractManager,
    web3: Web3,
    token_network_address: TokenNetworkAddress,
    start_block: BlockNumber,
    target_block: BlockNumber,
) -> Iterable[Dict]:
    """ Read all TokenNetwork events up to the current confirmed head. """

    chain_id = ChainID(web3.eth.chainId)
    filters = [token_network_events(token_network_address, contract_manager)]
    blockchain_events = BlockchainEvents(
        web3=web3,
        chain_id=chain_id,
        contract_manager=contract_manager,
        last_fetched_block=start_block,
        event_filters=filters,
        block_batch_size_config=BlockBatchSizeConfig(),
    )

    while target_block > blockchain_events.last_fetched_block:
        poll_result = blockchain_events.fetch_logs_in_batch(target_block)
        if poll_result is None:
            # No blocks could be fetched (due to timeout), retry
            continue

        for event in poll_result.events:
            yield event.event_data


def _get_token_network_address(
    token_address: TokenAddress, web3: Web3, privkey: PrivateKey, deploy: DeployedContracts
) -> TokenNetworkAddress:

    client = JSONRPCClient(web3, privkey, faster_gas_price_strategy)
    proxy_manager = get_proxy_manager(client, deploy)
    token_network_registry_address = TokenNetworkRegistryAddress(
        to_canonical_address(deploy["contracts"][CONTRACT_TOKEN_NETWORK_REGISTRY]["address"])
    )
    confirmed_block_hash = client.get_confirmed_blockhash()
    token_network_registry = proxy_manager.token_network_registry(
        token_network_registry_address, confirmed_block_hash
    )
    token_network_address = token_network_registry.get_token_network(
        token_address, confirmed_block_hash
    )
    assert token_network_address
    return token_network_address


def _withdraw_participant_left_capacity_from_channel(
    address_to_candidate: Dict[Address, ReclamationCandidate],
    channel: dict,
    token_network: TokenNetwork,
    current_confirmed_head: BlockIdentifier,
) -> None:
    """ Withdraw all tokens in channel to channel["participant1"] """
    assert token_network.client.address == channel["participant1"]

    # Check if channel still has deposits
    details = token_network.detail_participants(
        participant1=to_canonical_address(channel["participant1"]),
        participant2=to_canonical_address(channel["participant2"]),
        block_identifier=current_confirmed_head,
        channel_identifier=channel["channel_identifier"],
    )
    new_withdraw = WithdrawAmount(
        details.our_details.deposit
        - details.our_details.withdrawn
        + details.partner_details.deposit
        - details.partner_details.withdrawn
    )
    assert new_withdraw >= 0, "negative withdrawn should never happen."

    if new_withdraw == 0:
        log.info(
            "Participant has no left over capacity in the channel. Skipping channel.",
            channel=channel,
        )
        return

    partner_candidate = address_to_candidate.get(details.partner_details.address)
    if partner_candidate is None:
        log.error(
            "Both participants must be in list of reclamation_candidates. Skipping channel.",
            channel=channel,
        )
        return

    expiration_block = BlockExpiration(100000000000000)
    total_withdraw = WithdrawAmount(details.our_details.withdrawn + new_withdraw)
    packed_withdraw = pack_withdraw(
        canonical_identifier=CanonicalIdentifier(
            chain_identifier=token_network.chain_id(),
            token_network_address=token_network.address,
            channel_identifier=channel["channel_identifier"],
        ),
        participant=to_canonical_address(channel["participant1"]),
        total_withdraw=total_withdraw,
        expiration_block=expiration_block,
    )

    privkey = token_network.client.privkey
    try:
        token_network.set_total_withdraw(
            given_block_identifier=current_confirmed_head,
            channel_identifier=channel["channel_identifier"],
            total_withdraw=total_withdraw,
            expiration_block=expiration_block,
            participant=to_canonical_address(channel["participant1"]),
            partner=to_canonical_address(channel["participant2"]),
            participant_signature=LocalSigner(privkey).sign(packed_withdraw),
            partner_signature=LocalSigner(partner_candidate.privkey).sign(packed_withdraw),
        )
    except InsufficientEth:
        log.warning("Not enough ETH to withdraw", channel=channel)
    else:
        log.info("Withdraw successful", channel=channel, amount=new_withdraw)


def withdraw_all(
    address_to_candidate: Dict[Address, ReclamationCandidate],
    account: Account,
    web3: Web3,
    contract_manager: ContractManager,
    token_address: TokenAddress,
) -> None:
    """ Withdraws all tokens from all channels

    For this to work, both channel participants have to be in ``reclamation_candidates``.

    All tokens will be withdrawn to participant1, ignoring all balance proofs.
    By doing this, we can empty the channel in a single transaction without any
    wait times.
    """
    chain_id = ChainID(web3.eth.chainId)
    deploy = get_contracts_deployment_info(chain_id, RAIDEN_CONTRACT_VERSION)
    assert deploy
    assert account.privkey
    token_network_address = _get_token_network_address(
        token_address=token_address, web3=web3, privkey=account.privkey, deploy=deploy
    )
    token_network_deployed_at = BlockNumber(
        deploy["contracts"][CONTRACT_TOKEN_NETWORK_REGISTRY]["block_number"]
    )

    # This assumes that reclamation will be done after the scenarios have
    # executed, so we don't have to synchronize with the whole blockchain, just
    # up to the last block used by the scenario run. Since we don't know the
    # exact block, use the current confirmed head.
    #
    # This also assumes no RPC calls to pruned data will be performed, so the
    # target_block is never updated!
    confirmation_blocks = DEFAULT_NUMBER_OF_BLOCK_CONFIRMATIONS
    latest_block = web3.eth.getBlock(BLOCK_ID_LATEST)
    latest_block_number = latest_block["number"]
    current_confirmed_head = BlockNumber(latest_block_number - confirmation_blocks)

    # The block range is inclusive, meaning the block represented by
    # last_fetched_block is skipped, so the block used has to be one before, to
    # make sure the deployment block is included.
    start_fetching_at = BlockNumber(token_network_deployed_at - 1)

    all_network_events = _get_all_token_network_events(
        contract_manager=contract_manager,
        web3=web3,
        token_network_address=token_network_address,
        start_block=start_fetching_at,
        target_block=current_confirmed_head,
    )

    tracked_channels: Dict[ChannelID, Dict] = dict()

    # Ignore closed channels and if an address is not under our control. since
    # The withdraw will only work properly on open channel if performed by both
    # participants.
    for event in all_network_events:
        is_useful_channel_open = (
            event["event"] == ChannelEvent.OPENED
            and event["args"]["participant1"] in address_to_candidate
            and event["args"]["participant2"] in address_to_candidate
        )
        if is_useful_channel_open:
            tracked_channels[event["args"]["channel_identifier"]] = event["args"]

        is_useful_channel_close = event["event"] == ChannelEvent.CLOSED and (
            event["args"]["channel_identifier"] in tracked_channels
        )
        if is_useful_channel_close:
            del tracked_channels[event["args"]["channel_identifier"]]

    log.debug("Channels found", channels=len(tracked_channels))

    pool = Pool()
    for channel_open_event in tracked_channels.values():
        candidate = address_to_candidate[channel_open_event["participant1"]]
        proxy_manager = candidate.get_proxy_manager(web3, deploy)
        token_network = proxy_manager.token_network(token_network_address, current_confirmed_head)

        pool.spawn(
            _withdraw_participant_left_capacity_from_channel,
            address_to_candidate=address_to_candidate,
            channel=channel_open_event,
            token_network=token_network,
            current_confirmed_head=current_confirmed_head,
        )

    # Wait until all transactions are mined, at this point we are ignoring
    # errors.
    pool.join(raise_error=True)

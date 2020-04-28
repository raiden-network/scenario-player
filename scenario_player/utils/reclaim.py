import json
import pathlib
import time
from dataclasses import dataclass
from itertools import chain as iter_chain
from pathlib import Path
from typing import Dict, List, Tuple

import structlog
from eth_keyfile import decode_keyfile_json
from eth_typing import URI
from eth_utils import to_canonical_address, to_checksum_address
from raiden_contracts.contract_manager import ContractManager, get_contracts_deployment_info
from web3 import HTTPProvider, Web3

from raiden.accounts import Account
from raiden.exceptions import InsufficientEth
from raiden.messages.abstract import cached_property
from raiden.network.proxies.custom_token import CustomToken
from raiden.network.proxies.proxy_manager import ProxyManager
from raiden.network.rpc.client import EthTransfer, JSONRPCClient
from raiden.settings import RAIDEN_CONTRACT_VERSION
from raiden.utils.typing import BlockNumber, ChainID, ChecksumAddress, TokenAddress, TokenAmount
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
    eth_rpc_endpoint: URI,
):
    web3 = Web3(HTTPProvider(eth_rpc_endpoint))
    chain_id = ChainID(web3.eth.chainId)
    deploy = get_contracts_deployment_info(chain_id, RAIDEN_CONTRACT_VERSION)
    assert deploy

    address_to_proxy_manager: Dict[ChecksumAddress, ProxyManager] = dict()
    planned_withdraws: Dict[ChecksumAddress, Tuple[BlockNumber, TokenAmount]] = dict()

    log.info("Checking chain for deposits in UserDeposit contact")
    for node in reclamation_candidates:
        if node.address not in address_to_proxy_manager:
            client = JSONRPCClient(web3, node.privkey)
            address_to_proxy_manager[node.address] = get_proxy_manager(client, deploy)
        proxy_manager = address_to_proxy_manager[node.address]
        (userdeposit_proxy, user_token_proxy) = get_udc_and_corresponding_token_from_dependencies(
            chain_id=chain_id, proxy_manager=proxy_manager
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
        proxy_manager = address_to_proxy_manager[address]
        (userdeposit_proxy, user_token_proxy) = get_udc_and_corresponding_token_from_dependencies(
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
        eth_rpc_endpoint,
    )


def reclaim_erc20(
    reclamation_candidates: List[ReclamationCandidate],
    token_address: TokenAddress,
    contract_manager: ContractManager,
    account: Account,
    eth_rpc_endpoint: URI,
):
    web3 = Web3(HTTPProvider(eth_rpc_endpoint))

    reclaim_amount = 0

    log.info("Checking chain")
    for node in reclamation_candidates:
        client = JSONRPCClient(web3, node.privkey)
        token = CustomToken(client, token_address, contract_manager, "latest")

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
            token_address=token.address,
        )


def reclaim_eth(
    reclamation_candidates: List[ReclamationCandidate], account: Account, eth_rpc_endpoint: URI
):
    web3 = Web3(HTTPProvider(eth_rpc_endpoint))

    txs = []
    reclaim_amount = 0
    gas_price = web3.eth.gasPrice
    reclaim_tx_cost = gas_price * VALUE_TX_GAS_COST

    log.info("Checking chain")
    for node in reclamation_candidates:
        balance = web3.eth.getBalance(node.address)
        if balance > reclaim_tx_cost:
            drain_amount = balance - reclaim_tx_cost
            log.info("Reclaiming", from_address=node.address, amount=drain_amount.__format__(",d"))
            reclaim_amount += drain_amount
            client = JSONRPCClient(web3, node.privkey)
            assert account.address
            txs.append(
                client.transact(
                    EthTransfer(
                        to_address=account.address, value=drain_amount, gas_price=gas_price
                    )
                )
            )
        (node.node_dir / "reclaimed").touch()

    wait_for_txs(web3, txs, 1000)
    log.info("Reclaimed", reclaim_amount=reclaim_amount.__format__(",d"))

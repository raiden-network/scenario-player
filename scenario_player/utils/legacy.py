import json
import os
import pathlib
import time
from dataclasses import dataclass
from itertools import chain as iter_chain
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import click
import requests
import structlog
from eth_keyfile import decode_keyfile_json
from eth_typing import URI
from eth_utils import encode_hex, to_canonical_address, to_checksum_address
from raiden_contracts.contract_manager import ContractManager, get_contracts_deployment_info
from requests.adapters import HTTPAdapter  # ugly import, it'll be in py3.8
from web3 import HTTPProvider, Web3
from web3.exceptions import TransactionNotFound
from web3.types import TxReceipt

from raiden.accounts import Account
from raiden.exceptions import InsufficientEth
from raiden.messages.abstract import cached_property
from raiden.network.proxies.custom_token import CustomToken
from raiden.network.proxies.proxy_manager import ProxyManager
from raiden.network.rpc.client import EthTransfer, JSONRPCClient, TransactionSent
from raiden.settings import RAIDEN_CONTRACT_VERSION
from raiden.utils.typing import BlockNumber, ChainID, ChecksumAddress, TokenAddress, TokenAmount
from scenario_player.exceptions import ScenarioTxError
from scenario_player.utils.contracts import (
    get_proxy_manager,
    get_udc_and_corresponding_token_from_dependencies,
)

VALUE_TX_GAS_COST = 21_000

log = structlog.get_logger(__name__)


# Seriously requests? For Humans?
class TimeOutHTTPAdapter(HTTPAdapter):
    def __init__(self, *args, **kwargs):
        self.timeout = kwargs.pop("timeout", None)
        super().__init__(*args, **kwargs)

    def send(self, *args, **kwargs):
        if "timeout" not in kwargs or not kwargs["timeout"]:
            kwargs["timeout"] = self.timeout
        return super().send(*args, **kwargs)


class ConcatenableNone:
    def __radd__(self, other):
        return other


class DummyStream:
    def write(self, content):
        pass


class MutuallyExclusiveOption(click.Option):
    def __init__(self, *args, **kwargs):
        self.mutually_exclusive = set(kwargs.pop("mutually_exclusive", []))
        help = kwargs.get("help", "")
        if self.mutually_exclusive:
            ex_str = ", ".join(self.mutually_exclusive)
            kwargs["help"] = help + (
                " NOTE: This argument is mutually exclusive with " " arguments: [" + ex_str + "]."
            )
        super(MutuallyExclusiveOption, self).__init__(*args, **kwargs)

    def handle_parse_result(self, ctx, opts, args):
        if self.mutually_exclusive.intersection(opts) and self.name in opts:
            raise click.UsageError(
                f"Illegal usage: {self.name} is mutually exclusive with "
                f"arguments {', '.join(self.mutually_exclusive)}."
            )

        return super(MutuallyExclusiveOption, self).handle_parse_result(ctx, opts, args)


def wait_for_txs(web3: Web3, transactions: Iterable[TransactionSent], timeout: int = 360):
    start = time.monotonic()
    outstanding = None
    txhashes = set(transaction_sent.transaction_hash for transaction_sent in transactions)

    while txhashes and time.monotonic() - start < timeout:
        remaining_timeout = timeout - (time.monotonic() - start)
        if outstanding != len(txhashes) or int(remaining_timeout) % 10 == 0:
            outstanding = len(txhashes)
            log.debug(
                "Waiting for tx confirmations",
                outstanding=outstanding,
                timeout_remaining=int(remaining_timeout),
            )
        for txhash in txhashes.copy():
            # TODO: use `JsonRpcClient.poll_transaction` here?
            try:
                # FIXME: remove `encode_hex` when TxHash type is fixed
                tx: Optional[TxReceipt] = web3.eth.getTransactionReceipt(encode_hex(txhash))
            except TransactionNotFound:
                tx = None

            if tx and tx["blockNumber"] is not None:
                status = tx.get("status")
                if status is not None and status == 0:
                    raise ScenarioTxError(f"Transaction {encode_hex(txhash)} failed.")
                # we want to add 2 blocks as confirmation
                if tx["blockNumber"] + 2 < web3.eth.getBlock("latest")["number"]:
                    txhashes.remove(txhash)
            time.sleep(0.1)
        time.sleep(1)

    if len(txhashes):
        txhashes_str = ", ".join(encode_hex(txhash) for txhash in txhashes)
        raise ScenarioTxError(f"Timeout waiting for txhashes: {txhashes_str}")


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


def post_task_state_to_rc(scenario, task, state) -> None:
    from scenario_player.tasks.base import TaskState
    from scenario_player.tasks.execution import ParallelTask, SerialTask

    color = "#c0c0c0"
    if state is TaskState.RUNNING:
        color = "#ffbb20"
    elif state is TaskState.FINISHED:
        color = "#20ff20"
    elif state is TaskState.ERRORED:
        color = "#ff2020"

    fields = [
        {"title": "Scenario", "value": scenario.scenario.name, "short": True},
        {"title": "State", "value": state.name.title(), "short": True},
        {"title": "Level", "value": task.level, "short": True},
    ]
    if state is TaskState.FINISHED:
        fields.append({"title": "Duration", "value": task._duration, "short": True})
    if not isinstance(task, (SerialTask, ParallelTask)):
        fields.append({"title": "Details", "value": task._str_details, "short": False})
    task_name = task._name
    if task_name and isinstance(task_name, str):
        task_name = task_name.title().replace("_", " ")
    else:
        task_name = task.__class__.__name__
    send_rc_message(f"Task {task_name}", color, fields)


def send_rc_message(text: str, color: str, fields: List[Dict[str, str]]) -> None:
    rc_webhook_url = os.environ.get("RC_WEBHOOK_URL")
    if not rc_webhook_url:
        raise RuntimeError("Environment variable 'RC_WEBHOOK_URL' is missing")

    requests.post(
        rc_webhook_url, json={"attachments": [{"title": text, "color": color, "fields": fields}]}
    )

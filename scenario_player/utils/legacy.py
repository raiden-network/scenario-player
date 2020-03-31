import json
import os
import pathlib
import time
from itertools import chain as iter_chain
from pathlib import Path
from typing import Dict, Iterable, List, Optional

import click
import requests
import structlog
from eth_keyfile import decode_keyfile_json
from eth_typing import URI
from eth_utils import encode_hex, to_checksum_address
from requests.adapters import HTTPAdapter
from web3 import HTTPProvider, Web3
from web3.exceptions import TransactionNotFound
from web3.types import TxReceipt

from raiden.accounts import Account
from raiden.network.rpc.client import EthTransfer, JSONRPCClient, TransactionSent
from raiden.utils.typing import ChecksumAddress, PrivateKey
from scenario_player.exceptions import ScenarioTxError

RECLAIM_MIN_BALANCE = 10 ** 12  # 1 µEth (a.k.a. Twei, szabo)
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


def reclaim_eth(
    account: Account, eth_rpc_endpoint: URI, data_path: pathlib.Path, min_age_hours: int
):
    log.info("Starting eth reclaim", data_path=data_path, eth_rpc_endpoint=eth_rpc_endpoint)
    web3 = Web3(HTTPProvider(eth_rpc_endpoint))

    address_to_keyfile: Dict[ChecksumAddress, dict] = dict()
    address_to_privkey: Dict[ChecksumAddress, PrivateKey] = dict()
    for node_dir in iter_chain(data_path.glob("**/node_???"), data_path.glob("**/node_*_???")):
        scenario_name: Path = Path(node_dir.parent.name)
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
                address_to_keyfile[to_checksum_address(address)] = keyfile_content

    log.info("Reclaiming candidates", addresses=list(address_to_keyfile.keys()))

    txs = []
    reclaim_amount = 0

    log.info("Checking chain")
    for address, keyfile_content in address_to_keyfile.items():
        balance = web3.eth.getBalance(address)
        if balance > RECLAIM_MIN_BALANCE:
            if address not in address_to_privkey:
                address_to_privkey[address] = decode_keyfile_json(keyfile_content, b"")
            privkey = address_to_privkey[address]
            drain_amount = balance - (web3.eth.gasPrice * VALUE_TX_GAS_COST)
            log.info("Reclaiming", from_address=address, amount=drain_amount.__format__(",d"))
            reclaim_amount += drain_amount
            client = JSONRPCClient(web3, privkey)
            assert account.address
            txs.append(
                client.transact(
                    EthTransfer(
                        to_address=account.address, value=drain_amount, gas_price=web3.eth.gasPrice
                    )
                )
            )

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

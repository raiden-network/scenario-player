import time
from typing import Iterable, Optional

import click
import structlog
from eth_utils import encode_hex
from raiden_common.network.rpc.client import TransactionSent
from requests.adapters import HTTPAdapter  # ugly import, it'll be in py3.8
from web3 import Web3
from web3.exceptions import TransactionNotFound
from web3.types import TxReceipt

from scenario_player.exceptions import ScenarioTxError

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
        help_ = kwargs.get("help", "")
        if self.mutually_exclusive:
            ex_str = ", ".join(self.mutually_exclusive)
            kwargs["help"] = help_ + (
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
    txhashes = {transaction_sent.transaction_hash for transaction_sent in transactions}

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

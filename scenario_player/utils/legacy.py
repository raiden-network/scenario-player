import json
import os
import pathlib
import platform
import subprocess
import time
import uuid
from collections import defaultdict, deque
from datetime import datetime
from itertools import chain as iter_chain, islice
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union

import click
import mirakuru
import requests
import structlog
from eth_keyfile import decode_keyfile_json
from eth_utils import to_checksum_address
from mirakuru import AlreadyRunning, TimeoutExpired
from mirakuru.base import ENV_UUID, IGNORED_ERROR_CODES
from raiden_contracts.constants import CONTRACT_CUSTOM_TOKEN, CONTRACT_USER_DEPOSIT
from raiden_contracts.contract_manager import get_contracts_deployment_info
from requests.adapters import HTTPAdapter
from web3 import HTTPProvider, Web3
from web3.contract import Contract
from web3.exceptions import TransactionNotFound

from raiden.accounts import Account
from raiden.network.rpc.client import EthTransfer, JSONRPCClient, check_address_has_code
from raiden.settings import RAIDEN_CONTRACT_VERSION
from raiden.utils.typing import TransactionHash
from scenario_player.exceptions import ScenarioError, ScenarioTxError

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


class LogBuffer:
    def __init__(self, capacity=1000):
        self.buffer = deque([""], maxlen=capacity)

    def write(self, content):
        lines = list(content.splitlines())
        self.buffer[0] += lines[0]
        if lines == [""]:
            # Bare newline
            self.buffer.appendleft("")
        else:
            self.buffer.extendleft(lines[1:])

    def getlines(self, start, stop=None):
        if stop:
            slice_ = islice(self.buffer, start, stop)
        else:
            slice_ = islice(self.buffer, start)
        return reversed(list(slice_))


class ConcatenableNone:
    def __radd__(self, other):
        return other


class DummyStream:
    def write(self, content):
        pass


class ChainConfigType(click.ParamType):
    name = "chain-config"

    def get_metavar(self, param):  # pylint: disable=unused-argument,no-self-use
        return "<chain-name>:<eth-node-rpc-url>"

    def convert(self, value, param, ctx):  # pylint: disable=unused-argument
        name, _, rpc_url = value.partition(":")
        if name.startswith("http") or "" in (name, rpc_url):
            self.fail(f"Invalid value: {value}. Use {self.get_metavar(None)}.")
        return name, rpc_url


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


class HTTPExecutor(mirakuru.HTTPExecutor):
    def start(self, stdout=subprocess.PIPE, stderr=subprocess.PIPE):
        """ Merged copy paste from the inheritance chain with modified stdout/err behaviour """
        if self.pre_start_check():
            # Some other executor (or process) is running with same config:
            raise AlreadyRunning(self)

        if self.process is None:
            command = self.command
            if not self._shell:
                command = self.command_parts

            env = os.environ.copy()
            env[ENV_UUID] = self._uuid
            popen_kwargs = {
                "shell": self._shell,
                "stdin": subprocess.PIPE,
                "stdout": stdout,
                "stderr": stderr,
                "universal_newlines": True,
                "env": env,
            }
            if platform.system() != "Windows":
                popen_kwargs["preexec_fn"] = os.setsid
            self.process = subprocess.Popen(command, **popen_kwargs)

        self._set_timeout()

        self.wait_for(self.check_subprocess)
        return self

    def stop(self, sig=None, timeout=10):
        """ Copy paste job from `SimpleExecutor.stop()` to add the `timeout` parameter. """
        if self.process is None:
            return self

        if sig is None:
            sig = self._sig_stop

        try:
            os.killpg(self.process.pid, sig)
        except OSError as err:
            if err.errno in IGNORED_ERROR_CODES:
                pass
            else:
                raise

        def process_stopped():
            """Return True only only when self.process is not running."""
            return self.running() is False

        self._set_timeout(timeout)
        try:
            self.wait_for(process_stopped)
        except TimeoutExpired:
            log.warning("Timeout expired, killing process", process=self)
            pass

        self._kill_all_kids(sig)
        self._clear_process()
        return self

    def wait_for(self, wait_for):
        while self.check_timeout():
            if wait_for():
                return self
            time.sleep(self._sleep)

        log.fatal("Killing node", cmd=self._shell)
        self.kill()
        raise TimeoutExpired(self, timeout=self._timeout)

    def _set_timeout(self, timeout=None):
        """
        Forward ported from mirakuru==1.0.0:mirakuru.base::SimpleExecutor._set_timeout() since
        the ``timeout`` parameter has been removed in versions >= 1.1.0.
        """
        timeout = timeout or self._timeout

        if timeout:
            self._endtime = time.time() + timeout


def wait_for_txs(
    client_or_web3: Union[Web3, JSONRPCClient], txhashes: Set[TransactionHash], timeout: int = 360
):
    if isinstance(client_or_web3, Web3):
        web3 = client_or_web3
    else:
        web3 = client_or_web3.web3
    start = time.monotonic()
    outstanding = False
    txhashes = set(txhashes)
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
                tx = web3.eth.getTransactionReceipt(txhash)
            except TransactionNotFound:
                tx = None

            if tx and tx["blockNumber"] is not None:
                status = tx.get("status")
                if status is not None and status == 0:
                    raise ScenarioTxError(f"Transaction {txhash} failed.")
                # we want to add 2 blocks as confirmation
                if tx["blockNumber"] + 2 < web3.eth.getBlock("latest")["number"]:
                    txhashes.remove(txhash)
            time.sleep(0.1)
        time.sleep(1)
    if len(txhashes):
        txhashes_str = ", ".join(txhash for txhash in txhashes)
        raise ScenarioTxError(f"Timeout waiting for txhashes: {txhashes_str}")


def get_or_deploy_token(runner) -> Tuple[Contract, int]:
    """ Deploy or reuse  """
    token_contract = runner.contract_manager.get_contract(CONTRACT_CUSTOM_TOKEN)

    token_config = runner.definition.token
    if not token_config:
        token_config = {}
    address = token_config.get("address")
    block = token_config.get("block", 0)
    reuse = token_config.get("reuse", False)

    token_address_file = runner.definition.settings.sp_scenario_dir.joinpath("token.infos")
    if reuse:
        if address:
            raise ScenarioError('Token settings "address" and "reuse" are mutually exclusive.')
        if token_address_file.exists():
            token_data = json.loads(token_address_file.read_text())
            address = token_data["address"]
            block = token_data["block"]
    if address:
        check_address_has_code(
            client=runner.client,
            address=address,
            contract_name="Token",
            given_block_identifier="latest",
        )
        token_ctr = runner.client.new_contract_proxy(token_contract["abi"], address)

        log.debug(
            "Reusing token",
            address=to_checksum_address(address),
            name=token_ctr.contract.functions.name().call(),
            symbol=token_ctr.contract.functions.symbol().call(),
        )
        return token_ctr, block

    token_id = uuid.uuid4()
    now = datetime.now()
    name = token_config.get("name", f"Scenario Test Token {token_id!s} {now:%Y-%m-%dT%H:%M}")
    symbol = token_config.get("symbol", f"T{token_id!s:.3}")
    decimals = token_config.get("decimals", 0)

    log.debug("Deploying token", name=name, symbol=symbol, decimals=decimals)

    token_ctr, receipt = runner.client.deploy_single_contract(
        "CustomToken",
        runner.contract_manager.contracts["CustomToken"],
        constructor_parameters=(1, decimals, name, symbol),
    )
    contract_deployment_block = receipt["blockNumber"]
    contract_checksum_address = to_checksum_address(token_ctr.address)
    if reuse:
        token_address_file.write_text(
            json.dumps({"address": contract_checksum_address, "block": contract_deployment_block})
        )

    log.info("Deployed token", address=contract_checksum_address, name=name, symbol=symbol)
    return token_ctr, contract_deployment_block


def get_udc_and_token(runner) -> Tuple[Optional[Contract], Optional[Contract]]:
    """ Return contract proxies for the UserDepositContract and associated token """
    from scenario_player.runner import ScenarioRunner

    assert isinstance(runner, ScenarioRunner)

    udc_config = runner.definition.settings.services.udc

    if not udc_config.enable:
        return None, None

    udc_address = udc_config.address
    if udc_address is None:
        contracts = get_contracts_deployment_info(
            chain_id=runner.definition.settings.chain_id, version=RAIDEN_CONTRACT_VERSION
        )
        udc_address = contracts["contracts"][CONTRACT_USER_DEPOSIT]["address"]
    udc_abi = runner.contract_manager.get_contract_abi(CONTRACT_USER_DEPOSIT)
    udc_proxy = runner.client.new_contract_proxy(udc_abi, udc_address)

    ud_token_address = udc_proxy.functions.token().call()
    # FIXME: We assume the UD token is a CustomToken (supporting the `mint()` function)
    custom_token_abi = runner.contract_manager.get_contract_abi(CONTRACT_CUSTOM_TOKEN)
    ud_token_proxy = runner.client.new_contract_proxy(custom_token_abi, ud_token_address)

    return udc_proxy, ud_token_proxy


def mint_token_if_balance_low(
    token_contract: Contract,
    target_address: str,
    min_balance: int,
    fund_amount: int,
    gas_limit: int,
    mint_msg: str,
    no_action_msg: str = None,
) -> Optional[TransactionHash]:
    """ Check token balance and mint if below minimum """
    balance = token_contract.contract.functions.balanceOf(target_address).call()
    if balance < min_balance:
        mint_amount = fund_amount - balance
        log.debug(mint_msg, address=target_address, amount=mint_amount)
        return token_contract.transact("mintFor", gas_limit, mint_amount, target_address)
    else:
        if no_action_msg:
            log.debug(no_action_msg, balance=balance)

    return None


def reclaim_eth(account: Account, chain_str: str, data_path: pathlib.Path, min_age_hours: int):
    chain_name, chain_url = chain_str.split(":", maxsplit=1)
    log.info("in cmd", chain=chain_str, chain_name=chain_name, chain_url=chain_url)

    web3s: Dict[str, Web3] = {chain_name: Web3(HTTPProvider(chain_url))}
    log.info("Starting eth reclaim", data_path=data_path)

    address_to_keyfile = dict()
    address_to_privkey = dict()
    for node_dir in iter_chain(data_path.glob("**/node_???"), data_path.glob("**/node_*_???")):
        scenario_name: Path = node_dir.parent.name
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

    txs = defaultdict(set)
    reclaim_amount = defaultdict(int)
    for chain_name, web3 in web3s.items():
        log.info("Checking chain", chain=chain_name)
        for address, keyfile_content in address_to_keyfile.items():
            balance = web3.eth.getBalance(address)
            if balance > RECLAIM_MIN_BALANCE:
                if address not in address_to_privkey:
                    address_to_privkey[address] = decode_keyfile_json(keyfile_content, b"")
                privkey = address_to_privkey[address]
                drain_amount = balance - (web3.eth.gasPrice * VALUE_TX_GAS_COST)
                log.info(
                    "Reclaiming",
                    from_address=address,
                    amount=drain_amount.__format__(",d"),
                    chain=chain_name,
                )
                reclaim_amount[chain_name] += drain_amount
                client = JSONRPCClient(web3, privkey)
                txs[chain_name].add(
                    client.transact(
                        EthTransfer(
                            to_address=account.address,
                            value=drain_amount,
                            gas_price=web3.eth.gasPrice,
                        )
                    )
                )
    for chain_name, chain_txs in txs.items():
        wait_for_txs(web3s[chain_name], chain_txs, 1000)
    for chain_name, amount in reclaim_amount.items():
        log.info("Reclaimed", chain=chain_name, amount=amount.__format__(",d"))


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

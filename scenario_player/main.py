import functools
import json
import os
import sys
import tempfile
import traceback
from contextlib import AbstractContextManager, contextmanager, nullcontext
from datetime import datetime
from io import StringIO
from itertools import cycle, islice
from pathlib import Path
from tempfile import mkdtemp
from typing import IO, List, Sequence

import click
import gevent
import structlog
import yaml
from click.utils import LazyFile
from eth_typing import URI, HexStr
from eth_utils import to_canonical_address, to_checksum_address
from gevent.event import Event
from raiden_contracts.constants import CHAINNAME_TO_ID
from raiden_contracts.contract_manager import (
    ContractManager,
    DeployedContract,
    DeployedContracts,
    contracts_precompiled_path,
)
from urwid import ExitMainLoop
from web3 import HTTPProvider, Web3
from web3.middleware import simple_cache_middleware

import scenario_player.utils
from raiden.accounts import Account
from raiden.constants import Environment, EthClient
from raiden.log_config import _FIRST_PARTY_PACKAGES, configure_logging
from raiden.network.rpc.client import make_sane_poa_middleware
from raiden.network.rpc.middleware import faster_gas_price_strategy
from raiden.settings import DEFAULT_MATRIX_KNOWN_SERVERS, RAIDEN_CONTRACT_VERSION
from raiden.utils.cli import AddressType, EnumChoiceType, get_matrix_servers, option
from raiden.utils.typing import (
    TYPE_CHECKING,
    Address,
    Any,
    AnyStr,
    BlockTimeout,
    Dict,
    FeeAmount,
    Optional,
    TokenAddress,
    TokenAmount,
)
from scenario_player import __version__, tasks
from scenario_player.exceptions import ScenarioAssertionError, ScenarioError
from scenario_player.exceptions.cli import WrongPassword
from scenario_player.runner import ScenarioRunner
from scenario_player.tasks.base import collect_tasks
from scenario_player.ui import ScenarioUI, attach_urwid_logbuffer
from scenario_player.utils import DummyStream
from scenario_player.utils.configuration.settings import EnvironmentConfig
from scenario_player.utils.legacy import MutuallyExclusiveOption
from scenario_player.utils.reclaim import ReclamationCandidate, get_reclamation_candidates
from scenario_player.utils.version import get_complete_spec

if TYPE_CHECKING:
    from raiden.tests.utils.smoketest import RaidenTestSetup

log = structlog.get_logger(__name__)
DEFAULT_ENV_FILE = Path(__file__).parent / "environment" / "development.json"


def construct_log_file_name(sub_command, data_path, scenario_fpath: Path = None) -> str:
    directory = data_path
    if scenario_fpath:
        file_name = (
            f"scenario-player-{sub_command}_{scenario_fpath.stem}"
            f"_{datetime.now():%Y-%m-%dT%H:%M:%S}.log"
        )
        directory = directory.joinpath("scenarios", scenario_fpath.stem)
    else:
        file_name = f"scenario-player-{sub_command}_{datetime.now():%Y-%m-%dT%H:%M:%S}.log"
    return str(directory.joinpath(file_name))


def configure_logging_for_subcommand(log_file_name):
    Path(log_file_name).parent.mkdir(exist_ok=True, parents=True)
    click.secho(f"Writing log to {log_file_name}", fg="yellow")
    configure_logging(
        {"": "INFO", "raiden": "DEBUG", "scenario_player": "DEBUG"},
        debug_log_file_path=log_file_name,
        _first_party_packages=_FIRST_PARTY_PACKAGES | frozenset(["scenario_player"]),
        _debug_log_file_additional_level_filters={"scenario_player": "DEBUG"},
    )


def load_account_obj(keystore_file, password):
    with open(keystore_file, "r") as keystore:
        account = Account(json.load(keystore), password, keystore_file)
        assert account.address
        log.info("Using account", account=to_checksum_address(account.address))
        return account


def get_password(password, password_file):
    if password_file:
        password = open(password_file, "r").read().strip()
    if password == password_file is None:
        password = click.prompt(text="Please enter your password: ", hide_input=True)
    return password


def get_account(keystore_file, password):
    try:
        account = load_account_obj(keystore_file, password)
    except ValueError:
        raise WrongPassword
    return account


def key_password_options(func):
    """Decorator for adding '--keystore-file', '--password/--password-file' to subcommands."""

    @click.option("--keystore-file", required=True, type=click.Path(exists=True, dir_okay=False))
    @click.option(
        "--password-file",
        type=click.Path(exists=True, dir_okay=False),
        cls=MutuallyExclusiveOption,
        mutually_exclusive=["password"],
        default=None,
    )
    @click.option(
        "--password",
        envvar="ACCOUNT_PASSWORD",
        cls=MutuallyExclusiveOption,
        mutually_exclusive=["password-file"],
        default=None,
    )
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    return wrapper


def data_path_option(func):
    """Decorator for adding '--data-path' to subcommands."""

    @click.option(
        "--data-path",
        default=Path(str(Path.home().joinpath(".raiden", "scenario-player"))),
        type=click.Path(exists=False, dir_okay=True, file_okay=False),
        show_default=True,
    )
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    return wrapper


def environment_option(func):
    """Decorator for adding '--environment' to subcommands."""

    @click.option(
        "--environment",
        default=DEFAULT_ENV_FILE,
        help="A JSON file containing the settings for Eth-RPC, PFS, "
        "transport servers, env-type...",
        show_default=True,
        type=click.File(),
    )
    @functools.wraps(func)
    def wrapper(*args, environment: IO, **kwargs):
        return func(*args, environment=_load_environment(environment), **kwargs)

    return wrapper


@click.group(invoke_without_command=True, context_settings={"max_content_width": 120})
def main():
    # Disable printing stack traces by the hub, which breaks the TUI and
    # duplicates the traces.
    #
    # The code must be written with proper error handling, which requires
    # linking the result of every greenlet to its parent. Linking results in
    # error propagation, the behavior is that if a child greenlet dies because
    # of an exception, the exception is re-raised in the parent. If the
    # exception ends up reaching top-level (killing main) the full stacktrace
    # will be printed.
    gevent.get_hub().exception_stream = DummyStream()


@main.command(name="run")
@click.argument("scenario-file", type=click.File(), required=False)
@click.option("--auth", default="")
@click.option(
    "--ui/--no-ui",
    "enable_ui",
    default=sys.stdout.isatty(),
    help="En-/disable console UI. [default: auto-detect]",
)
@click.option(
    "--delete-snapshots",
    is_flag=True,
    help="Delete node snapshots for the given scenario if any are present.",
)
@click.option(
    "--raiden-client",
    default=None,
    help="The client executable to use [default set by `env` file]",
)
@environment_option
@key_password_options
@data_path_option
def run(
    data_path: str,
    auth: str,
    password: str,
    keystore_file: str,
    scenario_file: LazyFile,
    enable_ui: bool,
    password_file: str,
    environment: EnvironmentConfig,
    delete_snapshots: bool,
    raiden_client: Optional[str],
):
    """Execute a scenario as defined in scenario definition file.
    click entrypoint, this dispatches to `run_`.
    """
    data_path_path = Path(data_path)
    scenario_file_path = Path(scenario_file.name).absolute()
    log_file_name = construct_log_file_name("run", data_path_path, scenario_file_path)
    configure_logging_for_subcommand(log_file_name)
    run_(
        data_path=data_path_path,
        auth=auth,
        password=password,
        keystore_file=keystore_file,
        scenario_file=scenario_file_path,
        enable_ui=enable_ui,
        password_file=password_file,
        log_file_name=log_file_name,
        environment=environment,
        delete_snapshots=delete_snapshots,
        raiden_client=raiden_client,
    )


def _load_environment(environment_file: IO) -> EnvironmentConfig:
    """Load the environment JSON file and process matrix server list

    Nodes can be assigned to fixed matrix servers. To allow this, we must
    download the list of matrix severs.
    """
    environment = json.load(environment_file)
    assert isinstance(environment, dict)

    matrix_server_list = environment.pop(
        "matrix_server_list",
        DEFAULT_MATRIX_KNOWN_SERVERS[Environment(environment["environment_type"])],
    )
    matrix_servers: Sequence[URI] = get_matrix_servers(matrix_server_list)  # type: ignore
    if len(matrix_servers) < 4:
        matrix_servers = list(islice(cycle(matrix_servers), 4))

    return EnvironmentConfig(
        matrix_servers=matrix_servers,
        environment_file_name=environment_file.name,
        **environment,
    )


def run_(
    data_path: Path,
    auth: str,
    password: Optional[str],
    keystore_file: str,
    scenario_file: Path,
    enable_ui: bool,
    password_file: str,
    log_file_name: str,
    environment: EnvironmentConfig,
    delete_snapshots: bool,
    raiden_client: Optional[str],
    smoketest_deployment_data=None,
) -> None:
    """Execute a scenario as defined in scenario definition file.
    (Shared code for `run` and `smoketest` command).

    Calls :func:`exit` when done, with the following status codes:

        Exit code 1x
        There was a problem when starting up the SP, nodes, deploying tokens
        or setting up services. This points at an issue in the SP and of of its
        components.

        Exit code 2x
        There was an error when parsing or evaluating the given scenario definition file.
        This may be a syntax- or logic-related issue.

        Exit code 3x
        There was an assertion error while executing the scenario. This points
        to an error in a `raiden` component (the client, services or contracts).
    """
    log.info("Scenario Player version:", version_info=get_complete_spec())

    password = get_password(password, password_file)
    account = get_account(keystore_file, password)

    log_buffer = None
    if enable_ui:
        log_buffer = attach_urwid_logbuffer()

    # Dynamically import valid Task classes from scenario_player.tasks package.
    collect_tasks(tasks)

    # Start our Services
    report: Dict[str, str] = {}
    success = Event()
    success.clear()
    try:
        # We need to fix the log stream early in case the UI is active
        scenario_runner = ScenarioRunner(
            account=account,
            auth=auth,
            data_path=data_path,
            scenario_file=scenario_file,
            environment=environment,
            success=success,
            smoketest_deployment_data=smoketest_deployment_data,
            delete_snapshots=delete_snapshots,
            raiden_client=raiden_client,
        )
        if enable_ui:
            ui: AbstractContextManager = ScenarioUIManager(
                scenario_runner, log_buffer, log_file_name, success
            )
        else:
            ui = nullcontext()
        log.info("Startup complete")
        with ui:
            scenario_runner.run_scenario()
    except ScenarioAssertionError as ex:
        log.error("Run finished", result="assertion errors")
        if hasattr(ex, "exit_code"):
            exit_code = ex.exit_code
        else:
            exit_code = 30
        report.update(dict(subject=f"Assertion mismatch in {scenario_file.name}", message=str(ex)))
        exit(exit_code)
    except ScenarioError as ex:
        log.error("Run finished", result="scenario error", message=str(ex))
        if hasattr(ex, "exit_code"):
            exit_code = ex.exit_code
        else:
            exit_code = 20
        report.update(
            dict(
                subject=f"Invalid scenario {scenario_file.name}",
                message=traceback.format_exc(),
            )
        )
        exit(exit_code)
    except Exception as ex:
        log.exception("Exception while running scenario")
        if hasattr(ex, "exit_code"):
            exit_code = ex.exit_code  # type: ignore  # pylint: disable=no-member
        else:
            exit_code = 10
        report.update(
            dict(
                subject=f"Error running scenario {scenario_file.name}",
                message=traceback.format_exc(),
            )
        )
        exit(exit_code)
    else:
        exit_code = 0
        log.info("Run finished", result="success")
        report.update(dict(subject=f"Scenario successful {scenario_file.name}", message="Success"))
        log.info("Scenario player unwind complete")
        exit(exit_code)


class ScenarioUIManager(AbstractContextManager):
    def __init__(self, runner, log_buffer, log_file_name, success):
        self.ui = ScenarioUI(runner, log_buffer, log_file_name)
        self.success = success

    def __enter__(self):
        self.ui_greenlet = self.ui.run()
        return self.success

    def __exit__(self, exc_type, value, traceback):
        if exc_type is not None:
            # This will cause some exceptions to be in the log twice, but
            # that's better than not seeing the exception in the UI at all.
            log.exception()
        try:
            self.ui.set_success(self.success.is_set())
            log.warning("Press q to exit")
            while not self.ui_greenlet.ready():
                gevent.sleep(0.1)
        finally:
            if self.ui_greenlet is not None and not self.ui_greenlet.dead:
                self.ui_greenlet.kill(ExitMainLoop)
                self.ui_greenlet.join()


@main.command(name="reclaim-eth")
@click.option(
    "--min-age",
    default=72,
    show_default=True,
    help="Minimum account non-usage age before reclaiming eth. In hours.",
)
@click.option(
    "--reclaim-token",
    "reclaim_tokens",
    multiple=True,
    type=AddressType(),
    help="ERC20 token address for which tokens should also be reclaimed",
)
@click.option(
    "--withdraw-from-udc",
    is_flag=True,
    default=False,
    help="Withdraw and reclaim tokens deposited in the UserDeposit contract",
)
@key_password_options
@environment_option
@data_path_option
def reclaim_eth(
    min_age,
    reclaim_tokens: List[TokenAddress],
    withdraw_from_udc: bool,
    password,
    password_file,
    keystore_file,
    environment: EnvironmentConfig,
    data_path,
):
    eth_rpc_endpoint = environment.eth_rpc_endpoints[0]
    log.info("start cmd", eth_rpc_endpoint=eth_rpc_endpoint)

    data_path = Path(data_path)
    password = get_password(password, password_file)
    account = get_account(keystore_file, password)
    contract_manager = ContractManager(contracts_precompiled_path(RAIDEN_CONTRACT_VERSION))

    configure_logging_for_subcommand(construct_log_file_name("reclaim-eth", data_path))

    reclamation_candidates = get_reclamation_candidates(data_path, min_age)
    address_to_candidate: Dict[Address, ReclamationCandidate] = {
        to_canonical_address(c.address): c for c in reclamation_candidates
    }
    log.info("Reclaiming candidates", addresses=[c.address for c in reclamation_candidates])

    web3 = Web3(HTTPProvider(eth_rpc_endpoint))
    # TODO: maybe use `monkey_patch_web3` here
    web3.middleware_onion.inject(make_sane_poa_middleware, layer=0)
    web3.middleware_onion.add(simple_cache_middleware)
    web3.eth.setGasPriceStrategy(faster_gas_price_strategy)

    if withdraw_from_udc:
        scenario_player.utils.reclaim.withdraw_from_udc(
            reclamation_candidates=reclamation_candidates,
            contract_manager=contract_manager,
            web3=web3,
            account=account,
        )

    for token_address in reclaim_tokens:
        log.info("Starting ERC20 token reclaim", token=to_checksum_address(token_address))
        scenario_player.utils.reclaim.withdraw_all(
            address_to_candidate=address_to_candidate,
            token_address=token_address,
            contract_manager=contract_manager,
            web3=web3,
            account=account,
        )
        scenario_player.utils.reclaim.reclaim_erc20(
            reclamation_candidates=reclamation_candidates,
            token_address=token_address,
            contract_manager=contract_manager,
            web3=web3,
            account=account,
        )

    log.info("Starting ETH reclaim")
    scenario_player.utils.reclaim.reclaim_eth(
        reclamation_candidates=reclamation_candidates, web3=web3, account=account
    )


@main.command(name="version", help="Show versions of scenario_player and raiden environment.")
@click.option(
    "--short",
    is_flag=True,
    help="Only display scenario_player version string.",
    default=False,
)
def version(short):
    if short:
        click.secho(message=__version__)
    else:
        spec = get_complete_spec()
        click.secho(message=json.dumps(spec, indent=2))


def smoketest_deployed_contracts(contracts: Dict[str, Any]) -> DeployedContracts:
    return DeployedContracts(
        chain_id=CHAINNAME_TO_ID["smoketest"],
        contracts={
            name: DeployedContract(
                address=to_checksum_address(address),
                transaction_hash=HexStr(""),
                block_number=1,
                gas_cost=1000,
                constructor_arguments=[],
            )
            for name, address in contracts.items()
        },
        contracts_version=RAIDEN_CONTRACT_VERSION,
    )


@main.command(name="smoketest", help="Run a short self-test.")
@option(
    "--eth-client",
    type=EnumChoiceType(EthClient),
    default=EthClient.GETH.value,
    show_default=True,
    help="Which Ethereum client to run for the smoketests",
)
def smoketest(eth_client: EthClient):
    from raiden.network.utils import get_free_port
    from raiden.tests.utils.smoketest import setup_smoketest, step_printer

    free_port_generator = get_free_port()
    datadir = mkdtemp()

    captured_stdout = StringIO()

    with report() as (report_file, append_report):
        append_report("Setting up Smoketest")
        with step_printer(step_count=6, stdout=sys.stdout) as print_step:
            setup: RaidenTestSetup
            with setup_smoketest(
                eth_client=eth_client,
                print_step=print_step,
                free_port_generator=free_port_generator,
                debug=False,
                stdout=captured_stdout,
                append_report=append_report,
            ) as setup:
                deployment_data = smoketest_deployed_contracts(setup.contract_addresses)
                config_file = create_smoketest_config_file(setup, datadir)

                keystore_file = os.path.join(setup.args["keystore_path"], "keyfile")
                password_file = setup.args["password_file"].name
                print_step("Running scenario player")
                append_report("Scenario Player Log", captured_stdout.getvalue())
                env = EnvironmentConfig(
                    pfs_fee=FeeAmount(100),
                    environment_type="development",
                    environment_file_name="smoketest",
                    matrix_servers=[setup.args["matrix_server"]],
                    transfer_token=TokenAddress(bytes([1] * 20)),
                    pfs_with_fee=URI("http://www.example.com"),
                    eth_rpc_endpoints=[URI(setup.args["eth_rpc_endpoint"])],
                    ms_reward_with_margin=TokenAmount(1),
                    settlement_timeout_min=BlockTimeout(100),
                    raiden_client="raiden",
                )
                try:
                    run_(
                        data_path=Path(datadir),
                        auth="",
                        password=None,
                        keystore_file=keystore_file,
                        scenario_file=config_file,
                        enable_ui=False,
                        password_file=password_file,
                        log_file_name=report_file,
                        environment=env,
                        smoketest_deployment_data=deployment_data,
                        delete_snapshots=False,
                        raiden_client="raiden",
                    )
                except SystemExit as ex:
                    append_report("Captured", captured_stdout.getvalue())
                    if ex.code != 0:
                        print_step("Error when running scenario player", error=True)
                        sys.exit(ex.code)
                    else:
                        print_step("Smoketest successful!")


@contextmanager
def report(report_path=None, disable_debug_logfile=True):
    if report_path is None:
        report_file = tempfile.mktemp(suffix=".log")
    else:
        report_file = report_path
    click.secho(f"Report file: {report_file}", fg="yellow")
    configure_logging(
        logger_level_config={"": "INFO", "raiden": "DEBUG", "scenario_player": "DEBUG"},
        log_file=report_file,
        disable_debug_logfile=disable_debug_logfile,
    )

    def append_report(subject: str, data: Optional[AnyStr] = None) -> None:
        with open(report_file, "a", encoding="UTF-8") as handler:
            handler.write(f'{f" {subject.upper()} ":=^80}{os.linesep}')
            if data is not None:
                write_data: str
                if isinstance(data, bytes):
                    write_data = data.decode()
                else:
                    write_data = data
                handler.writelines([write_data + os.linesep])

    yield report_file, append_report


def create_smoketest_config_file(setup: "RaidenTestSetup", datadir: str) -> Path:
    udc_address = to_checksum_address(setup.args["user_deposit_contract_address"])
    config = yaml.safe_load(Path("tests/smoketests/template.yaml").read_text())
    config_file = Path(tempfile.mktemp(dir=datadir, suffix=".yaml"))
    config["nodes"]["default_options"]["user-deposit-contract-address"] = udc_address
    config["token"]["address"] = to_checksum_address(setup.token.address)
    with open(config_file, "w") as f:
        yaml.dump(config, f)
        log.info(f"Written scenario to {config_file}.")
    return config_file


if __name__ == "__main__":
    main()  # pylint: disable=no-value-for-parameter

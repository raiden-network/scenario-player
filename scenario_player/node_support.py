import errno
import hashlib
import json
import os
import platform
import shutil
import signal
import socket
import stat
import sys
from contextlib import closing
from pathlib import Path
from subprocess import Popen
from tarfile import TarFile
from typing import IO, TYPE_CHECKING, Any, Dict, List, Optional, Set, Tuple, Union
from urllib.parse import urljoin
from zipfile import ZipFile

import gevent
import requests
import structlog
from cachetools.func import ttl_cache
from eth_keyfile import create_keyfile_json
from eth_typing import URI
from eth_utils import to_checksum_address
from eth_utils.typing import ChecksumAddress
from gevent.pool import Group, Pool

from raiden.ui.cli import FLAG_OPTIONS, KNOWN_OPTIONS
from raiden.utils.nursery import Nursery
from scenario_player.exceptions import ScenarioError
from scenario_player.utils.configuration.nodes import NodesConfig

if TYPE_CHECKING:
    from scenario_player.runner import ScenarioRunner

log = structlog.get_logger(__name__)

RAIDEN_RELEASES_URL = "https://raiden-nightlies.ams3.digitaloceanspaces.com/"
RAIDEN_RELEASES_LATEST_FILE_TEMPLATE = "_LATEST-NIGHTLY-{platform}-{arch}.txt"
RAIDEN_RELEASES_VERSIONED_NAME_TEMPLATE = "raiden-v{version}-{platform}-{arch}.zip"


MANAGED_CONFIG_OPTIONS = {
    "accept-disclaimer",
    "address",
    "claims-file-path",
    "config-file",
    "datadir",
    "disable-debug-logfile",
    "eth-rpc-endpoint",
    "log-config",
    "log-file",
    "log-json",
    "network-id",
    "password-file",
    "rpc",
    "sync-check",
    "transport",
    "web-ui",
}

MANAGED_CONFIG_OPTIONS_OVERRIDABLE = {
    "api-address",
    "endpoint-registry-contract-address",
    "matrix-server",
    "pathfinding-service-address",
    "secret-registry-contract-address",
    "service-registry-contract-address",
    "tokennetwork-registry-contract-address",
}


class RaidenReleaseKeeper:
    def __init__(self, release_cache_dir: Path):
        self._downloads_path = release_cache_dir.joinpath("downloads")
        self._bin_path = release_cache_dir.joinpath("bin")

        self._downloads_path.mkdir(exist_ok=True, parents=True)
        self._bin_path.mkdir(exist_ok=True, parents=True)

    def get_release(self, version: str = "LATEST"):
        # `version` can also be a path
        bin_path = Path(version)
        if bin_path.exists() and bin_path.stat().st_mode & stat.S_IXUSR == stat.S_IXUSR:
            # File exists and is executable
            return bin_path

        if version.lower() == "latest":
            release_file_name = self._latest_release_name
        else:
            if version.startswith("v"):
                version = version.lstrip("v")
            release_file_name = self._expand_release_template(
                RAIDEN_RELEASES_VERSIONED_NAME_TEMPLATE, version=version
            )

        release_file_path = self._get_release_file(release_file_name)
        return self._get_bin_for_release(release_file_path)

    def _get_bin_for_release(self, release_file_path: Path):
        if not release_file_path.exists():
            raise ValueError(f"Release file {release_file_path} not found")

        archive: Union[TarFile, ZipFile]
        if release_file_path.suffix == ".gz":
            tar_opener = TarFile.open(release_file_path, "r:*")
            with tar_opener as tar_archive:
                contents = tar_archive.getnames()
            archive = tar_archive
        else:
            zip_opener = ZipFile(release_file_path, "r")
            with zip_opener as zip_archive:
                contents = zip_archive.namelist()
            archive = zip_archive

        if len(contents) != 1:
            raise ValueError(
                f"Release archive has unexpected content. "
                f'Expected 1 file, found {len(contents)}: {", ".join(contents)}'
            )

        bin_file_path = self._bin_path.joinpath(contents[0])
        if not bin_file_path.exists():
            log.debug(
                "Extracting Raiden binary",
                release_file_name=release_file_path.name,
                bin_file_name=bin_file_path.name,
            )
            archive.extract(contents[0], str(self._bin_path))
            bin_file_path.chmod(0o770)
        return bin_file_path

    def _get_release_file(self, release_file_name: str):
        release_file_path = self._downloads_path.joinpath(release_file_name)
        if release_file_path.exists():
            return release_file_path

        url = RAIDEN_RELEASES_URL + release_file_name
        release_file_path.parent.mkdir(exist_ok=True, parents=True)
        with requests.get(url, stream=True) as resp, release_file_path.open("wb+") as release_file:
            log.debug("Downloading Raiden release", release_file_name=release_file_name)
            if not 199 < resp.status_code < 300:
                raise ValueError(
                    f"Can't download release file {release_file_name}: "
                    f"{resp.status_code} {resp.text}"
                )
            shutil.copyfileobj(resp.raw, release_file)
        return release_file_path

    @property  # type: ignore
    @ttl_cache(maxsize=1, ttl=600)
    def _latest_release_name(self):
        latest_release_file_name = self._expand_release_template(
            RAIDEN_RELEASES_LATEST_FILE_TEMPLATE
        )
        url = urljoin(RAIDEN_RELEASES_URL, latest_release_file_name)
        log.debug("Fetching latest Raiden release", lookup_url=url)
        return requests.get(url).text.strip()

    @staticmethod
    def _expand_release_template(template, **kwargs):
        return template.format(
            platform="macOS" if sys.platform == "darwin" else sys.platform,
            arch=platform.machine(),
            **kwargs,
        )


class NodeRunner:
    def __init__(self, runner: "ScenarioRunner", index: int, raiden_version, options: dict):
        self._runner = runner
        self._index = index
        self._raiden_version = raiden_version
        self._options = options
        self._nursery: Optional[Nursery] = None
        if runner.definition.nodes.reuse_accounts:
            datadir_name = f"node_{index:03d}"
        else:
            datadir_name = f"node_{self._runner.run_number:04d}_{index:03d}"
        self.datadir = runner.definition.scenario_dir.joinpath(datadir_name)

        self._address: Optional[ChecksumAddress] = None
        self._api_address: Optional[str] = None

        self.claims_file: Optional[Path] = None

        self._output_files: Dict[str, IO] = {}

        if options.pop("_clean", False):
            shutil.rmtree(self.datadir)
        self.datadir.mkdir(parents=True, exist_ok=True)
        self._validate_options(options)
        self._eth_rpc_endpoint: URI = next(
            self._runner.definition.settings.eth_rpc_endpoint_iterator
        )
        self._process: Optional[Popen] = None

    def initialize(self):
        # Access properties to ensure they're initialized
        _ = self._keystore_file  # noqa: F841
        _ = self._raiden_bin  # noqa: F841

    def start(self, wait: bool = False):
        from scenario_player.runner import wait_for_nodes_to_be_ready

        log.info(
            "Starting node",
            node=self._index,
            address=self.address,
            port=self.api_address.rpartition(":")[2],
        )
        log.debug("Node start command", command=self._command)
        self._output_files["stdout"] = self._stdout_file.open("at", 1)
        self._output_files["stderr"] = self._stderr_file.open("at", 1)
        for file in self._output_files.values():
            file.write("--------- Starting ---------\n")
        self._output_files["stdout"].write(f"Command line: {' '.join(self._command)}\n")

        self._process = self.nursery.exec_under_watch(self._command, **self._output_files)
        if wait:
            wait_for_nodes_to_be_ready([self], self._runner.session)

    # FIXME: Make node stop configurable?
    def stop(self, timeout=600):  # 10 mins
        assert self._process is not None, "Can't call .stop() before .start()"
        self._process.send_signal(signal.SIGINT)
        if self._process.wait(timeout):
            raise Exception(f"Node {self._index} did not stop cleanly: ")

    @property
    def address(self) -> ChecksumAddress:
        if not self._address:
            with self._keystore_file.open("r") as keystore_file:
                keystore_contents = json.load(keystore_file)
            self._address = to_checksum_address(keystore_contents["address"])
        return self._address

    @property
    def base_url(self):
        return self.api_address

    @property
    def is_running(self):
        # `Popen.poll()` returns `None` if the process is still running
        return self._process is not None and self._process.poll() is None

    @property
    def _command(self) -> List[str]:
        cmd = [
            self._raiden_bin,
            "--accept-disclaimer",
            "--datadir",
            self.datadir,
            "--keystore-path",
            self._keystore_file.parent,
            "--address",
            self.address,
            "--password-file",
            self._password_file,
            "--network-id",
            self._runner.definition.settings.chain_id,
            "--sync-check",  # FIXME: Disable sync check for private chains
            "--gas-price",
            self._options.get("gas-price", "normal"),
            "--eth-rpc-endpoint",
            self._eth_rpc_endpoint,
            "--log-config",
            ":info,raiden:debug,raiden_contracts:debug,raiden.api.rest.pywsgi:warning",
            "--log-json",
            "--log-file",
            self._log_file,
            "--disable-debug-logfile",
            "--matrix-server",
            self._options.get("matrix-server", "auto"),
            "--api-address",
            self.api_address,
            "--no-web-ui",
        ]

        pfs_address = self._pfs_address
        if pfs_address:
            cmd.extend(["--pathfinding-service-address", pfs_address])

        if self.claims_file is not None and self.claims_file.exists():
            cmd.extend(["--claims-file-path", str(self.claims_file.absolute())])

        for option_name in MANAGED_CONFIG_OPTIONS_OVERRIDABLE:
            if option_name in ("api-address", "pathfinding-service-address", "matrix-server"):
                # already handled above
                continue
            if option_name in self._options:
                option_value = self._options[option_name]
                if not isinstance(option_value, list):
                    option_value = [option_value]
                cmd.extend([f"--{option_name}", *option_value])

        remaining_option_candidates = (
            KNOWN_OPTIONS - MANAGED_CONFIG_OPTIONS - MANAGED_CONFIG_OPTIONS_OVERRIDABLE
        )
        for option_name in remaining_option_candidates:
            if option_name in self._options:
                if option_name not in FLAG_OPTIONS:
                    option_value = self._options[option_name]
                    if not isinstance(option_value, list):
                        option_value = [option_value]
                    cmd.extend([f"--{option_name}", *option_value])
                else:
                    cmd.append(f"--{option_name}")

        # Ensure path instances are converted to strings
        cmd = [str(c) for c in cmd]
        return cmd

    @property
    def _raiden_bin(self):
        if self._raiden_version.lower() == "local":
            binary = shutil.which("raiden")
            if not binary:
                raise FileNotFoundError("Could not use local binary! No Binary found in env!")
            return binary
        return self._runner.release_keeper.get_release(self._raiden_version)

    @property
    def _keystore_file(self):
        keystore_path = self.datadir.joinpath("keys")
        keystore_path.mkdir(exist_ok=True, parents=True)
        keystore_file = keystore_path.joinpath("UTC--1")
        if not keystore_file.exists():
            log.debug("Initializing keystore", node=self._index)
            gevent.sleep()
            seed = (
                f"{self._runner.local_seed}"
                f"-{self._runner.definition.name}"
                f"-{self._runner.run_number}"
                f"-{self._index}"
            ).encode()
            privkey = hashlib.sha256(seed).digest()
            keystore_file.write_text(json.dumps(create_keyfile_json(privkey, b"", iterations=100)))
        else:
            log.debug("Reusing keystore", node=self._index)
        return keystore_file

    @property
    def _password_file(self):
        pw_file = self.datadir.joinpath("password.txt")
        pw_file.write_text("")
        return pw_file

    @property
    def api_address(self):
        if not self._api_address:
            self._api_address = self._options.get("api-address")
            if self._api_address is None:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                with closing(sock):
                    # Force the port into TIME_WAIT mode, ensuring that it will not
                    # be considered 'free' by the OS for the next 60 seconds. This
                    # does however require that the process using the port sets
                    # SO_REUSEADDR on it's sockets. Most 'server' applications do.
                    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    sock.bind(("127.0.0.1", 0))

                    sock_addr = sock.getsockname()
                    port = sock_addr[1]

                    # Connect to the socket to force it into TIME_WAIT state (see
                    # above)
                    sock.listen(1)
                    sock2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    with closing(sock2):
                        sock2.connect(sock_addr)
                        sock.accept()
                    self._api_address = f"127.0.0.1:{port}"
        return self._api_address

    @property
    def _log_file(self):
        return self.datadir.joinpath(f"run-{self._runner.run_number:03d}.log")

    @property
    def _stdout_file(self):
        return self.datadir.joinpath(f"run-{self._runner.run_number:03d}.stdout")

    @property
    def _stderr_file(self):
        return self.datadir.joinpath(f"run-{self._runner.run_number:03d}.stderr")

    @property
    def _pfs_address(self):
        local_pfs = self._options.get("pathfinding-service-address")
        global_pfs = self._runner.definition.settings.services.pfs.url
        if local_pfs:
            if global_pfs:
                log.warning(
                    "Overriding global PFS configuration",
                    global_pfs_address=global_pfs,
                    local_pfs_address=local_pfs,
                    node=self._index,
                )
            return local_pfs
        if global_pfs:
            return global_pfs

        return None

    def _validate_options(self, options: Dict[str, Any]):
        for option_name, option_value in options.items():
            if option_name.startswith("no-"):
                option_name = option_name.replace("no-", "")
            if option_name in MANAGED_CONFIG_OPTIONS:
                raise ScenarioError(
                    f'Raiden node option "{option_name}" is managed by the scenario player '
                    f"and cannot be changed."
                )
            if option_name in MANAGED_CONFIG_OPTIONS_OVERRIDABLE:
                log.warning(
                    "Overriding managed option",
                    option_name=option_name,
                    option_value=option_value,
                    node=self._index,
                )

            if option_name not in KNOWN_OPTIONS:
                raise ScenarioError(f'Unknown option "{option_name}" supplied.')

    @property
    def nursery(self):
        assert self._nursery is not None, "Nursery needs to be set before nodes can be started."
        return self._nursery

    @nursery.setter
    def nursery(self, value: Nursery):
        self._nursery = value


class SnapshotManager:
    def __init__(self, scenario_runner: "ScenarioRunner", node_runners: List[NodeRunner]) -> None:
        self._scenario_runner = scenario_runner
        self._node_runners = node_runners

    def check_scenario_config(self):
        if not self._scenario_runner.definition.nodes.reuse_accounts:
            raise ScenarioError("Snapshots aren't supported when 'nodes.reuse_accounts' is False.")

        token_config = self._scenario_runner.definition.token
        if (not token_config.should_reuse_token) and token_config.address is None:
            raise ScenarioError(
                "Snapshots are only supported when token reuse is enabled "
                "or a fixed token address is configured."
            )

    def _check_conditions(self):
        all_nodes_stopped = all(not node_runner.is_running for node_runner in self._node_runners)
        assert all_nodes_stopped, "Can't perform snapshot operations while nodes are running."
        self.check_scenario_config()

    def _get_snapshot_dirs(self) -> List[Path]:
        snapshot_dirs = []
        snapshot_base_dir = self._scenario_runner.definition.snapshot_dir
        for node_runner in self._node_runners:
            node_dir_suffix = node_runner.datadir.name

            snapshot_dir = snapshot_base_dir.joinpath(node_dir_suffix)
            snapshot_dirs.append(snapshot_dir)

        return snapshot_dirs

    def take(self) -> bool:
        self._check_conditions()
        snapshot_exists, snapshot_dirs = self.get_snapshot_info()
        if snapshot_exists:
            log.warning("Not retaking existing snapshot")
            return False
        log.info("Taking snapshot")
        source_target_pairs = zip(
            (node_runner.datadir for node_runner in self._node_runners), snapshot_dirs
        )
        for source, target in source_target_pairs:
            shutil.copytree(source, target)
        log.info("Snapshot taken")
        return True

    def restore(self) -> bool:
        self._check_conditions()
        snapshot_exists, snapshot_dirs = self.get_snapshot_info()
        if not snapshot_exists:
            log.info("Snapshot not found, skipping restore.")
            return False
        log.debug("Restoring snapshot")
        source_target_pairs = zip(
            snapshot_dirs, (node_runner.datadir for node_runner in self._node_runners)
        )
        for source, target in source_target_pairs:
            shutil.rmtree(target)
            shutil.copytree(source, target)
        log.info("Snapshot restored")
        return True

    def delete(self) -> None:
        self._check_conditions()
        snapshot_dir = self._scenario_runner.definition.snapshot_dir
        log.info("Deleting snapshots", snapshot_dir=snapshot_dir)
        shutil.rmtree(snapshot_dir)

    def get_snapshot_info(self) -> Tuple[bool, List[Path]]:
        snapshot_dirs = self._get_snapshot_dirs()
        dirs_exist = [snapshot_dir.exists() for snapshot_dir in snapshot_dirs]
        if any(dirs_exist) and not all(dirs_exist):
            missing_nodes = ", ".join(
                snapshot_dir.name for snapshot_dir in snapshot_dirs if not snapshot_dir.exists()
            )
            raise ScenarioError(
                f"Inconsistent snapshot. "
                f"Snapshot dirs for nodes {missing_nodes} are missing. "
                f"Use --delete-snapshots to clean."
            )
        elif not all(dirs_exist):
            return False, snapshot_dirs
        return True, snapshot_dirs


class NodeController:
    def __init__(
        self, runner: "ScenarioRunner", config: NodesConfig, delete_snapshots: bool = False
    ):
        self._runner = runner
        self._global_options = config.default_options
        self._node_options = config.node_options
        self._node_runners = [
            NodeRunner(
                runner,
                index,
                config.raiden_version,
                options={**self._global_options, **self._node_options.get(index, {})},
            )
            for index in range(config.count)
        ]
        self.snapshot_manager = SnapshotManager(runner, self._node_runners)
        self.snapshot_restored: bool = False
        if delete_snapshots:
            self.snapshot_manager.delete()
        if config.restore_snapshot:
            if self.snapshot_manager.restore():
                self.snapshot_restored = True
        log.info("Using Raiden version", version=config.raiden_version)

    def __getitem__(self, item):
        return self._node_runners[item]

    def __len__(self):
        return self._node_runners.__len__()

    def start(self, wait=True):
        from scenario_player.runner import wait_for_nodes_to_be_ready

        log.info("Starting nodes")

        # Start nodes in <number of cpus> batches
        pool = Pool(size=os.cpu_count())

        def _start():
            for runner in self._node_runners:
                pool.spawn(runner.start, wait=True)
            pool.join(raise_error=True)
            wait_for_nodes_to_be_ready(self._node_runners, self._runner.session)
            log.info("All nodes started")

        starter = gevent.spawn(_start)
        if wait:
            starter.get(block=True)
        return starter

    def stop(self):
        log.info("Stopping nodes")
        stop_group = Group()
        for runner in self._node_runners:
            stop_group.spawn(runner.stop)
        stop_group.join(raise_error=True)
        log.info("Nodes stopped")

    def initialize_nodes(self):
        for runner in self._node_runners:
            runner.initialize()

    @property
    def addresses(self) -> Set[ChecksumAddress]:
        return {runner.address for runner in self._node_runners}

    @property
    def address_to_index(self) -> Dict[ChecksumAddress, int]:
        return {runner.address: i for i, runner in enumerate(self._node_runners)}

    def set_nursery(self, nursery: Nursery):
        for node_runner in self._node_runners:
            node_runner.nursery = nursery

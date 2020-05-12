import hashlib
import json
import os
import platform
import shutil
import signal
import socket
import stat
import sys
from pathlib import Path
from tarfile import TarFile
from typing import IO, TYPE_CHECKING, Any, Dict, List, Optional, Set, Union
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
from gevent import Greenlet
from gevent.pool import Pool

from raiden.ui.cli import FLAG_OPTIONS, KNOWN_OPTIONS
from raiden.utils.nursery import Nursery
from scenario_player.exceptions import ScenarioError

if TYPE_CHECKING:
    from scenario_player.runner import ScenarioRunner

log = structlog.get_logger(__name__)

RAIDEN_RELEASES_URL = "https://raiden-nightlies.ams3.digitaloceanspaces.com/"
RAIDEN_RELEASES_LATEST_FILE_TEMPLATE = "_LATEST-NIGHTLY-{platform}-{arch}.txt"
RAIDEN_RELEASES_VERSIONED_NAME_TEMPLATE = "raiden-v{version}-{platform}-{arch}.zip"


MANAGED_CONFIG_OPTIONS = {
    "accept-disclaimer",
    "address",
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
    def __init__(
        self, runner: "ScenarioRunner", index: int, raiden_version, options: dict, nursery
    ):
        self._runner = runner
        self._index = index
        self._raiden_version = raiden_version
        self._options = options
        self._nursery = nursery
        self._datadir = runner.definition.scenario_dir.joinpath(
            f"node_{self._runner.run_number}_{index:03d}"
        )

        self._address: Optional[ChecksumAddress] = None
        self._api_address: Optional[str] = None

        self._output_files: Dict[str, IO] = {}

        if options.pop("_clean", False):
            shutil.rmtree(self._datadir)
        self._datadir.mkdir(parents=True, exist_ok=True)
        self._validate_options(options)
        self._eth_rpc_endpoint: URI = next(
            self._runner.definition.settings.eth_rpc_endpoint_iterator
        )

    def initialize(self):
        # Access properties to ensure they're initialized
        _ = self._keystore_file  # noqa: F841
        _ = self._raiden_bin  # noqa: F841

    def start(self):
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

        self._process = self._nursery.exec_under_watch(self._command, **self._output_files)

    # FIXME: Make node stop configurable?
    def stop(self, timeout=600):  # 10 mins
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
    def _command(self) -> List[str]:
        cmd = [
            self._raiden_bin,
            "--accept-disclaimer",
            "--datadir",
            self._datadir,
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

        for option_name in MANAGED_CONFIG_OPTIONS_OVERRIDABLE:
            if option_name in ("api-address", "pathfinding-service-address", "matrix-server"):
                # already handled above
                continue
            if option_name in self._options:
                option_value = self._options[option_name]
                if isinstance(option_value, list):
                    cmd.extend([f"--{option_name}", *self._options[option_name]])
                else:
                    cmd.extend([f"--{option_name}", self._options[option_name]])

        remaining_option_candidates = (
            KNOWN_OPTIONS - MANAGED_CONFIG_OPTIONS - MANAGED_CONFIG_OPTIONS_OVERRIDABLE
        )
        for option_name in remaining_option_candidates:
            if option_name in self._options:
                if option_name not in FLAG_OPTIONS:
                    option_value = self._options[option_name]
                    if isinstance(option_value, list):
                        cmd.extend([f"--{option_name}", *self._options[option_name]])
                    else:
                        cmd.extend([f"--{option_name}", self._options[option_name]])
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
        keystore_path = self._datadir.joinpath("keys")
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
            keystore_file.write_text(json.dumps(create_keyfile_json(privkey, b"")))
        return keystore_file

    @property
    def _password_file(self):
        pw_file = self._datadir.joinpath("password.txt")
        pw_file.write_text("")
        return pw_file

    @property
    def api_address(self):
        if not self._api_address:
            self._api_address = self._options.get("api-address")
            if self._api_address is None:
                # Find a random free port
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.bind(("127.0.0.1", 0))
                self._api_address = f"127.0.0.1:{sock.getsockname()[1]}"
                sock.close()
        return self._api_address

    @property
    def _log_file(self):
        return self._datadir.joinpath(f"run-{self._runner.run_number:03d}.log")

    @property
    def _stdout_file(self):
        return self._datadir.joinpath(f"run-{self._runner.run_number:03d}.stdout")

    @property
    def _stderr_file(self):
        return self._datadir.joinpath(f"run-{self._runner.run_number:03d}.stderr")

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


class NodeController:
    def __init__(self, runner: "ScenarioRunner", config, nursery: Nursery):
        self._runner = runner
        self._global_options = config.default_options
        self._node_options = config.node_options
        self._node_runners = [
            NodeRunner(
                runner,
                index,
                config.raiden_version,
                options={**self._global_options, **self._node_options.get(index, {})},
                nursery=nursery,
            )
            for index in range(config.count)
        ]
        log.info("Using Raiden version", version=config.raiden_version)

    def __getitem__(self, item):
        return self._node_runners[item]

    def __len__(self):
        return self._node_runners.__len__()

    def start(self, wait=True):
        log.info("Starting nodes")

        # Start nodes in <number of cpus> batches
        pool = Pool(size=os.cpu_count())

        def _start():
            for runner in self._node_runners:
                pool.start(Greenlet(runner.start))
            pool.join(raise_error=True)
            log.info("All nodes started")

        starter = gevent.spawn(_start)
        if wait:
            starter.get(block=True)
        return starter

    def stop(self):
        log.info("Stopping nodes")
        stop_tasks = set(gevent.spawn(runner.stop) for runner in self._node_runners)
        gevent.joinall(stop_tasks, raise_error=True)
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

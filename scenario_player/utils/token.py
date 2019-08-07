import json
import pathlib
from typing import Dict, Tuple, Union

import structlog
from eth_utils import to_checksum_address

from raiden.constants import GAS_LIMIT_FOR_TOKEN_CONTRACT_CALL
from raiden.network.rpc.client import AddressWithoutCode, check_address_has_code
from scenario_player.exceptions.config import (
    TokenFileError,
    TokenFileMissing,
    TokenNotDeployed,
    TokenSourceCodeDoesNotExist,
)
from scenario_player.services.utils.interface import ServiceInterface

log = structlog.get_logger(__name__)


class Contract:
    def __init__(self, runner, address=None):
        self._address = address
        self.config = runner.yaml
        self._local_rpc_client = runner.client
        self._local_contract_manager = runner.contract_manager
        self.interface = ServiceInterface(runner.yaml.spaas)
        self.gas_limit = GAS_LIMIT_FOR_TOKEN_CONTRACT_CALL * 2

    @property
    def client_id(self):
        return self.config.spaas.rpc.client_id

    @property
    def address(self):
        return self._address

    @property
    def balance(self):
        return self._local_rpc_client.balance(self.address)

    @property
    def checksum_address(self) -> str:
        """Checksum'd address of the deployed contract."""
        return to_checksum_address(self.address)

    def mint(self, target_address):
        """Mint new tokens for the given `target_address`.

        The amount of tokens depends on the scenario yaml's settings, and defaults to
        :attr:`.DEFAULT_TOKEN_BALANCE_MIN` and :attr:`.DEFAULT_TOKEN_BALANCE_FUND`
        if those settings are absent.
        """
        balance = self.balance
        if balance < self.config.token.min_balance:
            mint_amount = self.config.token.max_funding - balance
            params = {
                "client_id": self.client_id,
                "gas_limit": self.config.gas_limit,
                "amount": mint_amount,
                "contract_address": self.address,
                "target_address": target_address,
            }
            resp = self.interface.post("spaas://rpc/token/mint", json=params)
            resp.raise_for_status()
            return resp.json()


class Token(Contract):
    """Token Contract data and configuration class.

    Takes care of setting up a token for the scenario run:

        - Loads configuration for token deployment
        - Loads data from token.info file if reusing an existing token
        - Deploys tokens to the blockchain, if required
        - Saves token contract data to file for reuse in later scenario runs
    """

    def __init__(self, scenario_runner, data_path: pathlib.Path):
        super(Token, self).__init__(scenario_runner)
        self._token_file = data_path.joinpath("token.info")
        self.contract_data = {}
        self.deployment_receipt = None

    @property
    def name(self) -> str:
        """Name of the token contract, as defined in the config."""
        return self.contract_data.get("name") or self.config.token.name

    @property
    def symbol(self) -> str:
        """Symbol of the token, as defined in the scenario config."""
        return self.config.token.symbol

    @property
    def decimals(self) -> int:
        """Number of decimals to use for the tokens."""
        return self.config.token.decimals

    @property
    def address(self) -> str:
        """Return the address of the token contract.

        While not deployed, this reads the addres from :attr:`TokenConfig.address`.

        As soon as it's deployed we use the returned contract data at
        :attr:`.contract_data` instead.
        """
        try:
            return self.contract_data["address"]
        except KeyError:
            return self.config.token.address

    @property
    def deployment_block(self) -> int:
        """Return the token contract's deployment block number.

        It is an error to access this property before the token is deployed.
        """
        try:
            return self.deployment_receipt.get("blockNumber")
        except AttributeError:
            # deployment_receipt is empty, token not deployed.
            raise TokenNotDeployed

    @property
    def deployed(self) -> bool:
        """Check if this token has been deployed yet."""
        try:
            return self.deployment_block is not None
        except TokenNotDeployed:
            return False

    @property
    def balance(self) -> float:
        """Return the token contract's balance.

        It is an error to access this property before the token is deployed.
        """
        if self.deployed:
            return super(Token, self).balance
        else:
            raise TokenNotDeployed

    def load_from_file(self) -> Dict[str, Union[str, int]]:
        """Load token configuration from disk.

        Stored information consists of:

            * token name
            * deployment block
            * contract address

        The data is a JSONEncoded dict, which is deserialized before being returned.
        This then looks like this::

            {
                "name": "<token name>",
                "address":, "<contract address>",
                "block": <deployment block},
            }

        :raises TokenFileError:
            if the file's contents cannot be loaded using the :mod:`json`
            module, or an expected key is absent.
        :raises TokenInfoFileMissing:
            if the user tries to re-use this token, but no token.info file
            exists for it in the data-path.
        """
        try:
            token_data = json.loads(self._token_file.read_text())
            if not all(k in token_data for k in ("address", "name", "block")):
                raise KeyError
        except KeyError as e:
            raise TokenFileError("Token data file is missing one or more required keys!") from e
        except json.JSONDecodeError as e:
            raise TokenFileError("Token data file corrupted!") from e
        except FileNotFoundError as e:
            raise TokenFileMissing("Token file does not exist!") from e
        return token_data

    def save_token(self) -> None:
        """Save token information to disk, for use in later scenario runs.

        Creates a `token.info` file in the `data_path`, if it does not exist already.

        Stored information consists of:

            * token name
            * deployment block
            * contract address

        And is stored as a JSONEncoded string::

            '{"name": "<token name>", "address": "<contract address>", "block": <deployment block}'


        """
        token_data = {
            "address": self.checksum_address,
            "block": self.deployment_block,
            "name": self.name,
        }

        # Make sure to create the path, if it does not exist.
        if not self._token_file.exists():
            self._token_file.parent.mkdir(exist_ok=True, parents=True)
            self._token_file.touch(exist_ok=True)

        # Store the address and block number of this token contract on disk.
        self._token_file.write_text(json.dumps(token_data))

    def init(self):
        """Load an existing or deploy a new token contract.O"""
        if self.config.token.reuse_token:
            return self.use_existing()
        return self.deploy_new()

    def use_existing(self) -> Tuple[str, int]:
        """Reuse an existing token, loading its data from the scenario's `token.info` file.

        :raises TokenSourceCodeDoesNotExist:
            If no source code is present at the loaded address.
        """
        token_data = self.load_from_file()
        contract_name, address, block = (
            token_data["name"],
            token_data["address"],
            token_data["block"],
        )
        try:
            check_address_has_code(
                self._local_rpc_client, address=address, contract_name=contract_name
            )
        except AddressWithoutCode as e:
            raise TokenSourceCodeDoesNotExist(
                f"Cannot reuse token - address {address} has no code stored!"
            ) from e

        # Fetch the token's contract_proxy data.
        contract_proxy = self._local_contract_manager.get_contract(contract_name)

        self.contract_data = {"token_contract": address, "name": contract_proxy.name}
        self.deployment_receipt = {"blockNum": block}
        checksummed_address = to_checksum_address(address)

        log.debug(
            "Reusing token",
            address=checksummed_address,
            name=contract_proxy.name,
            symbol=contract_proxy.symbol,
        )
        return checksummed_address, block

    def deploy_new(self) -> Tuple[str, int]:
        """Returns the proxy contract address of the token contract, and the creation receipt.

        Since this involves sending a transaction via the network, we send a request
        to the `rpc` SP Service.

        The returned values are assigned to :attr:`.contract_data` and :attr:`.deployment_receipt`.

        Should the `reuse` option be set to `True`, the token information is saved to
        disk, in a `token.info` file of the current scenario's `data_dir` folder
        (typically `~/.raiden/scenario-player/<scenario>/token.info`).
        """
        log.debug("Deploying token", name=self.name, symbol=self.symbol, decimals=self.decimals)

        resp = self.interface.post(
            "spaas://rpc/token",
            json={
                "client_id": self.client_id,
                "constructor_args": {
                    "decimals": self.decimals,
                    "name": self.name,
                    "symbol": self.symbol,
                },
                "token_name": self.name,
            },
        )
        resp_data = resp.json()
        if "error" in resp_data:
            raise TokenNotDeployed(f"Error {resp_data['error']: {resp_data['message']}}")

        token_contract_data, deployment_block = (
            resp_data["contract"],
            resp_data["deployment_block"],
        )

        # Make deployment address and block available to address/deployment_block properties.
        self.contract_data = token_contract_data
        self.deployment_receipt = {"blockNumber": deployment_block}

        if self.config.token.reuse_token:
            self.save_token()

        log.info(
            "Deployed token", address=self.checksum_address, name=self.name, symbol=self.symbol
        )
        return self.address, self.deployment_block


class UserDepositContract(Contract):
    """User Deposit Contract wrapper for scenario runs.

    Takes care of:

        - Minting tokens for nodes on the UDC
        - Updating the allowance of nodes
    """

    def __init__(self, scenario_runner, contract_proxy, token_proxy):
        super(UserDepositContract, self).__init__(
            scenario_runner, address=contract_proxy.contract_address
        )
        self.contract_proxy = contract_proxy
        self.token_proxy = token_proxy
        self.tx_hashes = set()

    def init(self):
        self.update_allowance()

    @property
    def allowance(self):
        return self.token_proxy.contract.functions.allowance(
            self._local_rpc_client.address, self.address
        ).call()

    def update_allowance(self):
        node_count = self.config.nodes.count
        udt_allowance = self.allowance

        if udt_allowance < self.config.token.min_balance * node_count:
            allow_amount = (self.config.token.max_funding * 10 * node_count) - udt_allowance
            log.debug("Updating UD token allowance", allowance=allow_amount)
            params = {
                "client_id": self.client_id,
                "constructor_args": {
                    "gas_limit": self.gas_limit,
                    "udc_address": self.address,
                    "allowance_amount": allow_amount,
                },
            }
            resp = self.interface.put(f"spaas://rpc/token/allowance", json=params)
            self.tx_hashes.add(resp.json()["tx_hash"])

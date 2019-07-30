import json
import pathlib
from typing import Dict, Tuple, Union

import structlog
from eth_utils import to_checksum_address

from raiden.network.rpc.client import AddressWithoutCode, check_address_has_code
from scenario_player.exceptions.config import (
    TokenFileError,
    TokenFileMissing,
    TokenNotDeployed,
    TokenSourceCodeDoesNotExist,
)
from scenario_player.services.utils.interface import ServiceInterface

log = structlog.get_logger(__name__)


class Token:
    """Token Contract data and configuration class.

    Takes care of setting up a token for the scenario run:

        - Loads configuration for token deployment
        - Loads data from token.info file if reusing an existing token
        - Deploys tokens to the blockchain, if required
        - Saves token contract data to file for reuse in later scenario runs
    """

    def __init__(self, yaml_config, scenario_runner, data_path: pathlib.Path):
        self.config = yaml_config.token
        self._local_rpc_client = scenario_runner.client
        self._local_contract_manager = scenario_runner.contract_manager
        self._token_file = data_path.joinpath("token.info")
        self.contract_data = {}
        self.deployment_receipt = None
        self.interface = ServiceInterface(yaml_config.spaas)

    @property
    def name(self) -> str:
        """Name of the token contract, as defined in the config."""
        return self.contract_data.get("contract_name") or self.config.name

    @property
    def symbol(self) -> str:
        """Symbol of the token, as defined in the scenario config."""
        return self.config.symbol

    @property
    def decimals(self) -> int:
        """Number of decimals to use for the tokens."""
        return self.config.decimals

    @property
    def address(self) -> str:
        """Return the address of the token contract.

        While not deployed, this reads the addres from :attr:`TokenConfig.address`.

        As soon as it's deployed we use the returned contract data at
        :attr:`.contract_data` instead.
        """
        try:
            return self.contract_data["contract_address"]
        except KeyError:
            return self.config.address

    @property
    def checksum_address(self) -> str:
        """Checksum'd address of the deployed contract."""
        return to_checksum_address(self.address)

    @property
    def deployment_block(self) -> int:
        """Return the token contract's deployment block number.

        It is an error to access this property before the token is deployed.
        """
        try:
            return self.deployment_receipt.get("blockNum")
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
            return self._local_rpc_client.balance(self.address)
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
        if self.config.reuse_token:
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
            "spaas://rpc/client/{client_id}/token",
            params={
                "constructor_args": [0, self.decimals, self.name, self.symbol],
                "token_name": self.name,
            },
        )
        resp_data = resp.json()
        token_contract_data, receipt = resp_data["contract"], resp_data["receipt"]

        # Make deployment address and block available to address/deployment_block properties.
        self.contract_data = token_contract_data
        self.deployment_receipt = receipt

        if self.config.reuse_token:
            self.save_token()

        log.info(
            "Deployed token", address=self.checksum_address, name=self.name, symbol=self.symbol
        )
        return self.address, self.deployment_block

    def mint(self, node_address, gas_limit):
        """Mint new tokens for the given `address`.

        The amount of tokens depends on the scenario yaml's settings, and defaults to
        :attr:`.DEFAULT_TOKEN_BALANCE_MIN` and :attr:`.DEFAULT_TOKEN_BALANCE_FUND`
         if those settings are absent.
        """
        token_balance_min = self.config.min_balance
        token_balance_fund = self.config.max_funding

        balance = self.balance
        if balance < token_balance_min:
            mint_amount = token_balance_fund - balance
            params = {
                "action": "mintFor",
                "gas_limit": gas_limit,
                "amount": mint_amount,
                "target_address": node_address,
            }
            log.debug("Minting tokens", contract=self, token=self.name, parameters=params)
            resp = self.interface.post("spaas://rpc/client/{client_id}/token/mint", params=params)
            resp.raise_for_status()
            return resp.json()

from pathlib import Path
from typing import Callable, Optional, Union

import structlog

from raiden.utils.typing import ChainID
from scenario_player.constants import (
    BB_ETH_RPC_ADDRESS,
    DEFAULT_CLIENT,
    DEFAULT_NETWORK,
    GAS_STRATEGIES,
    TIMEOUT,
)
from scenario_player.exceptions.config import (
    ScenarioConfigurationError,
    ServiceConfigurationError,
    UDCTokenConfigError,
)
from scenario_player.utils.configuration.base import ConfigMapping
from scenario_player.utils.types import NetlocWithPort

log = structlog.get_logger(__name__)


class PFSSettingsConfig(ConfigMapping):
    """UDC Service Settings interface.

    Example scenario definition::

        >my_scenario.yaml
        version: 2
        ...
        settings:
          ...
          services:
            ...
            pfs:
              url: http://pfs.raiden.network
            ...
    """

    def __init__(self, loaded_definition: dict):
        super(PFSSettingsConfig, self).__init__(
            loaded_definition.get("settings").get("services", {}).get("pfs", {})  # type: ignore
        )
        self.validate()

    @property
    def url(self):
        return self.get("url")


class UDCTokenSettings(ConfigMapping):
    """UDC Token Settings Interface.

    Example scenario definition::

        >my_scenario.yaml
          ---
            udc:
              ...
              token:
                deposit: false
                balance_per_node: 5000
                max_funding: 5000
            ...
    """

    CONFIGURATION_ERROR = UDCTokenConfigError

    def __init__(self, loaded_definition: dict):
        udc_settings = ((loaded_definition.get("settings") or {}).get("services") or {}).get(
            "udc"
        ) or {}
        super(UDCTokenSettings, self).__init__(udc_settings.get("token"))
        self.validate()

    def validate(self) -> None:
        """Validate the UDC Token options given.

        :raises UDCTokenConfigError: if :attr:`.max_funding` < :attr:`.balance_per_node`.
        """
        self.assert_option(
            self.max_funding >= self.balance_per_node,
            "udc.token.max_funding must be >= udc.token.balance_per_node!",
        )

    @property
    def deposit(self) -> bool:
        """Whether or not to deposit tokens at nodes.

        If this is set to False or not given, the attributes :attr:`.max_funding` and
        :attr:`.balance_per_node` will not be used.

        Defaults to True.
        """
        return self.get("deposit", True)

    @property
    def balance_per_node(self) -> int:
        """The required amount of UDC/RDN tokens required by each node."""
        return int(self.get("balance_per_node", 5000))

    @property
    def max_funding(self) -> int:
        """The maximum amount to fund when depositing RDN tokens at a target.

        It defaults to :attr:`.balance_per_node`'s value.
        """
        return int(self.get("max_funding", self.balance_per_node))


class UDCSettingsConfig(ConfigMapping):
    """UDC Service Settings interface.

    Example scenario definition::

        >my_scenario.yaml
        version: 2
        ...
        settings:
          ...
          services:
            udc:
              enable: True
              address: 0x1000001
              token:
                <UDCTokenSettings>
            ...
    """

    def __init__(self, loaded_definition: dict):
        services_dict = (loaded_definition.get("settings") or {}).get("services") or {}
        super(UDCSettingsConfig, self).__init__(services_dict.get("udc", {}))
        self.validate()
        self.token = UDCTokenSettings(loaded_definition)

    @property
    def enable(self) -> bool:
        return self.get("enable", False)

    @property
    def address(self) -> Union[str, None]:
        return self.get("address")


class ServiceSettingsConfig(ConfigMapping):
    """Service Configuration Setting interface.

    Does nothing special but delegate attribute-based access
    to raiden service settings.
    """

    CONFIGURATION_ERROR = ServiceConfigurationError

    def __init__(self, loaded_definition: dict):
        super(ServiceSettingsConfig, self).__init__(
            (loaded_definition.get("settings") or {}).get("services") or {}
        )
        self.pfs = PFSSettingsConfig(loaded_definition)
        self.udc = UDCSettingsConfig(loaded_definition)
        self.validate()


class SettingsConfig(ConfigMapping):
    """Settings Configuration Setting interface and validator.

    Handles default values as well as exception handling on missing settings.

    The configuration present at the given path will automatically be checked for
    critical errors, such as missing or mutually exclusive keys.

    Example scenario definition::

        >my_scenario.yaml
        version: 2
        ...
        settings:
          timeout: 55
          notify: False
          chain: any
          gas_price: fast
          services:
            <ServicesSettingsConfig>
        ...

    """

    CONFIGURATION_ERROR = ScenarioConfigurationError

    def __init__(self, loaded_definition: dict) -> None:
        super(SettingsConfig, self).__init__(loaded_definition.get("settings") or {})
        self.services = ServiceSettingsConfig(loaded_definition)
        self.validate()
        # If chain or rpc address are given via CLI, they override the scenario
        # definition values. These attributes store these overrides.
        self._cli_rpc_address: Optional[str] = None
        self._cli_chain: Optional[str] = None
        self.chain_id: Optional[ChainID] = None
        self.sp_root_dir: Optional[Path] = None
        self._sp_scenario_root_dir = None

    @property
    def sp_scenario_root_dir(self):
        if not self._sp_scenario_root_dir:
            self._sp_scenario_root_dir = self.sp_root_dir.joinpath("scenarios")
            self._sp_scenario_root_dir.mkdir(exist_ok=True, parents=True)

        return self._sp_scenario_root_dir

    def validate(self):
        self.assert_option(
            isinstance(self.gas_price, (int, str)),
            f"Gas Price must be an integer or one of "
            f"{list(GAS_STRATEGIES.keys())}, not {self.gas_price}",
        )
        if isinstance(self.gas_price, str):
            self.assert_option(
                self.gas_price in GAS_STRATEGIES,
                f"Gas Price must be an integer or one of "
                f"{list(GAS_STRATEGIES.keys())}, not {self.gas_price}",
            )

    @property
    def timeout(self) -> int:
        """Returns the scenario's set timeout in seconds."""
        return self.get("timeout", TIMEOUT)

    @property
    def notify(self) -> Union[str, None]:
        """Return the email address to which notifications are to be sent.

        If this isn't set, we return None.
        """
        return self.get("notify")

    @property
    def chain(self) -> str:
        """Return the name of the chain to be used for this scenario.

        Defaults to :var:`DEFAULT_NETWORK` test net.
        """
        chain = self.get("chain", DEFAULT_NETWORK)
        return self._cli_chain or chain

    @property
    def eth_client(self) -> str:
        """Return the Ethereum Client to use.

        This should be the name of the executable, not a path.

        Defaults to :var:`DEFAULT_CLIENT`.
        """
        return self.get("eth-client", DEFAULT_CLIENT)

    @property
    def eth_client_rpc_address(self) -> NetlocWithPort:
        """Return the Ethereum client's RPC address.

        The value is loaded in the following order:

            - `--chain` value passed via CLI
            - `eth-client-rpc-address` value in the scenario definition file
            - :var:`BB_ETH_RPC_ADDRESS`, populated with values of
             :attr:`.chain` and :attr:`.eth_client`.

        """
        rpc_address = self.get(
            "eth-client-rpc-address",
            BB_ETH_RPC_ADDRESS.format(network=self.chain, client=self.eth_client),
        )
        return NetlocWithPort(self._cli_rpc_address or rpc_address)

    @property
    def gas_price(self) -> Union[str, int]:
        """Return the configured gas price for this scenario.

        This defaults to 'fast'.
        """
        gas_price = self.get("gas_price", "fast")

        if isinstance(gas_price, str):
            return gas_price.upper()

        assert isinstance(gas_price, int)
        return gas_price

    @property
    def gas_price_strategy(self) -> Callable:
        """Return the gas price strategy callable requested in :attr:`.gas_price`.

        If the price is an int, the callable will always return :attr:`.gas_price`.

        If the price is a string, we fetch the appropriate callable from :mod:`web3`.

        :raises ValueError: If the strategy cannot be found.
        """
        if isinstance(self.gas_price, int):

            def fixed_gas_price(*_, **__):
                return self.gas_price

            return fixed_gas_price

        try:
            return GAS_STRATEGIES[self.gas_price]
        except KeyError:
            raise ValueError(f'Invalid gas_price value: "{self.gas_price}"')

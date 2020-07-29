import itertools
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, Optional, Sequence, Union

import structlog
from eth_typing import URI
from typing_extensions import Literal

from raiden.utils.typing import (
    BlockTimeout,
    ChainID,
    ChecksumAddress,
    FeeAmount,
    TokenAddress,
    TokenAmount,
)
from scenario_player.constants import GAS_STRATEGIES, TIMEOUT
from scenario_player.exceptions.config import (
    ScenarioConfigurationError,
    ServiceConfigurationError,
    UDCTokenConfigError,
)

log = structlog.get_logger(__name__)


@dataclass
class EnvironmentConfig:
    environment_file_name: str
    environment_type: Union[Literal["production"], Literal["development"]]
    matrix_servers: Sequence[Union[URI, Literal["auto"]]]
    pfs_with_fee: URI
    eth_rpc_endpoints: List[URI]
    eth_rpc_endpoint_iterator: Iterator[URI] = field(init=False)
    transfer_token: TokenAddress
    pfs_fee: FeeAmount
    ms_reward_with_margin: TokenAmount
    settlement_timeout_min: BlockTimeout

    def __post_init__(self):
        self.eth_rpc_endpoint_iterator = itertools.cycle(self.eth_rpc_endpoints)


class PFSSettingsConfig:
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
        settings = loaded_definition.get("settings", {})
        services = settings.get("services", {})
        pfs = services.get("pfs", {})
        self.dict = pfs

    @property
    def url(self):
        return self.dict.get("url")


class UDCTokenSettings:
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

    def __init__(self, loaded_definition: dict, environment: EnvironmentConfig):
        settings = loaded_definition.get("settings", {})
        services = settings.get("services", {})
        udc_settings = services.get("udc", {})
        self.dict = udc_settings.get("token", {})
        self.environment = environment
        self.validate()

    def validate(self) -> None:
        """Validate the UDC Token options given.

        :raises UDCTokenConfigError: if :attr:`.max_funding` < :attr:`.balance_per_node`.
        """
        assert (
            self.max_funding >= self.balance_per_node
        ), "udc.token.max_funding must be >= udc.token.balance_per_node!"

    @property
    def deposit(self) -> bool:
        """Whether or not to deposit tokens at nodes.

        If this is set to False or not given, the attributes :attr:`.max_funding` and
        :attr:`.balance_per_node` will not be used.

        Defaults to True.
        """
        flag = self.dict.get("deposit", True)
        assert isinstance(flag, bool)
        return flag

    @property
    def balance_per_node(self) -> int:
        """The required amount of UDC/RDN tokens required by each node."""
        return int(self.dict.get("balance_per_node", 50 * self.environment.pfs_fee))

    @property
    def max_funding(self) -> int:
        """The maximum amount to fund when depositing RDN tokens at a target.

        It defaults to :attr:`.balance_per_node`'s value.
        """
        return int(self.dict.get("max_funding", self.balance_per_node))


class UDCSettingsConfig:
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

    def __init__(self, loaded_definition: dict, environment: EnvironmentConfig):
        settings = loaded_definition.get("settings", {})
        services = settings.get("services", {})
        self.dict = services.get("udc", {})
        self.environment = environment
        self.token = UDCTokenSettings(loaded_definition, environment)

    @property
    def enable(self) -> bool:
        flag = self.dict.get("enable", False)
        assert isinstance(flag, bool)
        return flag

    @property
    def address(self) -> Optional[ChecksumAddress]:
        address = self.dict.get("address")
        if address is None:
            return None

        return ChecksumAddress(address)


class ServiceSettingsConfig:
    """Service Configuration Setting interface.

    Does nothing special but delegate attribute-based access
    to raiden service settings.
    """

    CONFIGURATION_ERROR = ServiceConfigurationError

    def __init__(self, loaded_definition: dict, environment: EnvironmentConfig):
        settings = loaded_definition.get("settings", {})
        services = settings.get("services", {})
        self.dict = services
        self.pfs = PFSSettingsConfig(loaded_definition)
        self.udc = UDCSettingsConfig(loaded_definition, environment)


class ClaimsConfig:
    def __init__(self, settings: Dict[str, Any]) -> None:
        config = settings.get("claims", {})

        self.enabled = config.get("enabled", False)
        self.hub_node_index = int(config.get("hub-node", -1))
        self.additional_address_count = int(config.get("additional-address-count", 0))
        self.token_amount = TokenAmount(int(config.get("token_amount", 100_000)))
        self.num_direct_channels = int(config.get("num_direct_channels", 0))

    def __repr__(self) -> str:
        return (
            f"<ClaimsConfig "
            f"enabled={self.enabled} "
            f"hub-node={self.hub_node_index} "
            f"additional-address-count={self.additional_address_count} "
            f"token_amount={self.token_amount} "
            f"num_direct-channels={self.num_direct_channels}>"
        )


class SettingsConfig:
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
          gas_price: fast
          services:
            <ServicesSettingsConfig>
        ...

    """

    CONFIGURATION_ERROR = ScenarioConfigurationError

    def __init__(self, loaded_definition: dict, environment: EnvironmentConfig) -> None:
        settings = loaded_definition.get("settings", {})
        self.dict = settings
        self.services = ServiceSettingsConfig(loaded_definition, environment)
        self.claims = ClaimsConfig(settings)
        self.validate()
        self.eth_rpc_endpoint_iterator: Iterator[URI]
        self.chain_id: ChainID
        self.sp_root_dir: Optional[Path] = None
        self._sp_scenario_root_dir: Optional[Path] = None

    @property
    def sp_scenario_root_dir(self):
        if not self._sp_scenario_root_dir:
            assert self.sp_root_dir
            self._sp_scenario_root_dir = self.sp_root_dir.joinpath("scenarios")
            self._sp_scenario_root_dir.mkdir(exist_ok=True, parents=True)

        return self._sp_scenario_root_dir

    def validate(self):
        assert isinstance(self.gas_price, (int, str)), (
            f"Gas Price must be an integer or one of "
            f"{list(GAS_STRATEGIES.keys())}, not {self.gas_price}"
        )

        if isinstance(self.gas_price, str):
            assert self.gas_price in GAS_STRATEGIES, (
                f"Gas Price must be an integer or one of "
                f"{list(GAS_STRATEGIES.keys())}, not {self.gas_price}"
            )

    @property
    def timeout(self) -> int:
        """Returns the scenario's set timeout in seconds."""
        timeout = self.dict.get("timeout", TIMEOUT)
        assert isinstance(timeout, int)
        return timeout

    @property
    def gas_price(self) -> Union[str, int]:
        """Return the configured gas price for this scenario.

        This defaults to 'fast'.
        """
        gas_price = self.dict.get("gas_price", "fast")

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

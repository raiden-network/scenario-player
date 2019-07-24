from typing import Callable, Union

import structlog

from scenario_player.constants import TIMEOUT
from scenario_player.exceptions.config import ScenarioConfigurationError, ServiceConfigurationError
from scenario_player.utils import get_gas_price_strategy
from scenario_player.utils.configuration.base import ConfigMapping

log = structlog.get_logger(__name__)


class PFSSettingsConfig(ConfigMapping):
    """UDC Service Settings interface.

    Example scenario yaml::

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

    def __init__(self, loaded_yaml: dict):
        super(PFSSettingsConfig, self).__init__(
            loaded_yaml.get("settings").get("services", {}).get("pfs", {})
        )
        self.validate()

    @property
    def url(self):
        return self.get("url")


class UDCSettingsConfig(ConfigMapping):
    """UDC Service Settings interface.

    Example scenario yaml::

        >my_scenario.yaml
        version: 2
        ...
        settings:
          ...
          services:
            ...
            udc:
              enable: True
              address: 0x1000001
              token:
                deposit: True
            ...
    """

    def __init__(self, loaded_yaml: dict):
        super(UDCSettingsConfig, self).__init__(
            loaded_yaml.get("settings").get("services", {}).get("udc", {})
        )
        self.validate()

    @property
    def enable(self):
        return self.get("enable", False)

    @property
    def address(self):
        return self.get("address")

    @property
    def token(self):
        return self.get("token", {"deposit": False})


class ServiceSettingsConfig(ConfigMapping):
    """Service Configuration Setting interface.

    Does nothing special but delegate attribute-based access
    to raiden service settings.
    """

    CONFIGURATION_ERROR = ServiceConfigurationError

    def __init__(self, loaded_yaml: dict):
        super(ServiceSettingsConfig, self).__init__(
            loaded_yaml.get("settings").get("services", {})
        )
        self.pfs = PFSSettingsConfig(loaded_yaml)
        self.udc = UDCSettingsConfig(loaded_yaml)
        self.validate()


class SettingsConfig(ConfigMapping):
    """Settings Configuration Setting interface and validator.

    Handles default values as well as exception handling on missing settings.

    The configuration present at the given path will automatically be checked for
    critical errors, such as missing or mutually exclusive keys.

    Example scenario yaml::

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

    def __init__(self, loaded_yaml: dict) -> None:
        super(SettingsConfig, self).__init__(loaded_yaml.get("settings", {}))
        self.services = ServiceSettingsConfig(loaded_yaml)
        self.validate()

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
        """Return the name of the chain to be used for this scenario."""
        return self.get("chain", "any")

    @property
    def gas_price(self) -> str:
        """Return the configured gas price for this scenario.

        This defaults to 'fast'.
        """
        return self.get("gas_price", "fast")

    @property
    def gas_price_strategy(self) -> Callable:
        return get_gas_price_strategy(self.gas_price)

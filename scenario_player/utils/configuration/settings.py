from typing import Callable, Optional, Union

import structlog

from scenario_player.constants import TIMEOUT
from scenario_player.exceptions.config import ScenarioConfigurationError
from scenario_player.utils import get_gas_price_strategy
from scenario_player.utils.configuration.base import ConfigMapping

log = structlog.get_logger(__name__)


class SettingsConfig(ConfigMapping):
    """Thin wrapper class around a scenario .yaml file.

    Handles default values as well as exception handling on missing settings.

    The configuration present at the given path will automatically be checked for
    critical errors, such as missing or mutually exclusive keys.
    """

    def __init__(self, loaded_yaml: dict) -> None:
        super(SettingsConfig, self).__init__(loaded_yaml.get("settings", {}))
        self.validate()

    @staticmethod
    def assert_option(expression, err: Optional[Union[str, Exception]] = None):
        """Assert the given expression and raise a ScenarioConfigurationError if it fails."""
        if isinstance(err, str):
            err = ScenarioConfigurationError(err)
        return ConfigMapping.assert_option(expression, err)

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
    def services(self):
        """ Return the configuration for raiden services, if available."""
        return self.get("services", {})

    @property
    def gas_price(self) -> str:
        """Return the configured gas price for this scenario.

        This defaults to 'fast'.
        """
        return self.get("gas_price", "fast")

    @property
    def gas_price_strategy(self) -> Callable:
        return get_gas_price_strategy(self.gas_price)

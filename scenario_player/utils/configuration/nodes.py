from typing import List, Optional, Union

import structlog

from scenario_player.exceptions.config import NodeConfigurationError
from scenario_player.utils.configuration.base import ConfigMapping

log = structlog.get_logger(__name__)


class NodesConfig(ConfigMapping):
    """Thin wrapper around the 'nodes' setting section of a loaded scenario .yaml file.

    Validates the givne config for missing values and mutually exclusive options.

    :param loaded_yaml: The dict loaded from the scenario yaml file.
    :param scenario_version: Version of the scenario yaml file.
    """

    CONFIGURATION_ERROR = NodeConfigurationError

    def __init__(self, loaded_yaml: dict):
        super(NodesConfig, self).__init__(loaded_yaml.get("nodes", {}))
        self.validate()

    @property
    def raiden_version(self) -> str:
        return self.dict.get("raiden_version", "LATEST")

    @property
    def count(self):
        return self["count"]

    @property
    def default_options(self) -> dict:
        return self.dict.get("default_options", {})

    @property
    def node_options(self) -> dict:
        return self.get("node_options", {})

    @property
    def list(self) -> List[str]:
        """Return the list of nodes configured in the scenario's yaml."""
        return self["list"]

    @property
    def commands(self) -> dict:
        """Return the commands configured for the nodes."""
        return self.get("commands", {})

    def validate(self):
        """Assert that the given configuration is valid.

        Ensures the following statements are True:

            * The scenario version is > 1
            * The configuration is not empty
            * The "list" option is present in the config
            * The "count" option is present in the config

        """
        self.assert_option(self.dict, "Must specify 'nodes' setting section!")
        self.assert_option("list" in self.dict, 'Must specify nodes under "list" setting!')
        self.assert_option("count" in self.dict, 'Must specify a "count" setting!')

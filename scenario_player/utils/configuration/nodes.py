import structlog

from scenario_player.exceptions.config import NodeConfigurationError
from scenario_player.utils.configuration.base import ConfigMapping

log = structlog.get_logger(__name__)


class NodesConfig(ConfigMapping):
    """Raiden nodes config settings interface.

    Thin wrapper around the 'nodes' setting section of a loaded scenario .yaml file.

    Validates the givne config for missing values and mutually exclusive options.


    Example scenario yaml::

        >my_scenario.yaml
        version: 2
        ...
        nodes:
          raiden_version:
          default_options:
            gas_price: fast
          node_options:
            0:
              gas_price: slow
          commands:

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
        """Default CLI flags to pass when starting any node."""
        return self.dict.get("default_options", {})

    @property
    def node_options(self) -> dict:
        """Node-specific overrides for the CLI options of nodes."""
        return self.get("node_options", {})

    @property
    def commands(self) -> dict:
        """Return the commands configured for the nodes."""
        return self.get("commands", {})

    def validate(self):
        """Assert that the given configuration is valid.

        Ensures the following statements are True:

            * The scenario version is > 1
            * The configuration is not empty
            * The "count" option is present in the config
            * If "node_options" is present, make sure its a dict of type `Dict[int, dict]`
        """
        self.assert_option(self.dict, "Must specify 'nodes' setting section!")
        self.assert_option("count" in self.dict, 'Must specify a "count" setting!')
        if self.node_options:
            self.assert_option(all(isinstance(k, int) for k in self.node_options.keys()))
            self.assert_option(all(isinstance(v, dict) for v in self.node_options.values()))

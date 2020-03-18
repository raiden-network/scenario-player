import structlog

from scenario_player.exceptions.config import NodeConfigurationError

log = structlog.get_logger(__name__)


class NodesConfig:
    """Raiden nodes config settings interface.

    Thin wrapper around the 'nodes' setting section of a loaded scenario .yaml file.

    Validates the givne config for missing values and mutually exclusive options.


    Example scenario definition::

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

    def __init__(self, loaded_definition: dict, environment=None):
        self.dict = loaded_definition.get("nodes") or {}

        if environment is not None:
            default_options = self.dict.get("default_options", {})
            if "environment-type" not in default_options:
                default_options["environment-type"] = environment
            self.dict["default_options"] = default_options
        self.validate()

    @property
    def raiden_version(self) -> str:
        return self.dict.get("raiden_version", "LATEST")

    @property
    def count(self):
        return self.dict["count"]

    @property
    def default_options(self) -> dict:
        """Default CLI flags to pass when starting any node."""
        return self.dict.get("default_options", {})

    @property
    def node_options(self) -> dict:
        """Node-specific overrides for the CLI options of nodes."""
        return self.dict.get("node_options", {})

    @property
    def commands(self) -> dict:
        """Return the commands configured for the nodes."""
        return self.dict.get("commands", {})

    def validate(self):
        """Assert that the given configuration is valid.

        Ensures the following statements are True:

            * The scenario version is > 1
            * The configuration is not empty
            * The "count" option is present in the config
            * If "node_options" is present, make sure its a dict of type `Dict[int, dict]`
        """
        assert self.dict, "Must specify 'nodes' setting section!"
        assert "count" in self.dict, 'Must specify a "count" setting!'

        if self.node_options:
            assert all(isinstance(k, int) for k in self.node_options.keys())
            assert all(isinstance(v, dict) for v in self.node_options.values())

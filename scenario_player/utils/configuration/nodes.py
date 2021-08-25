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
          default_options:
            gas_price: fast
          reuse_accounts:
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
    def count(self):
        return self.dict["count"]

    @property
    def reuse_accounts(self) -> bool:
        """Should node accounts be re-used across scenario runs."""
        return self.dict.get("reuse_accounts", False)

    @property
    def restore_snapshot(self) -> bool:
        return self.dict.get("restore_snapshot", False)

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
            * The `count` option is present in the config and is an integer
            * If `reuse_accounts` is present it must be a boolean
            * If `restore_snapshot` is present it must be a string.
            * If `restore_snapshot` is not None, `reuse_accounts` must be `True`
            * If `node_options` is present, make sure its of type `Dict[int, Dict[str, Any]]`
        """
        assert self.dict, "Must specify 'nodes' setting section!"
        assert "count" in self.dict, 'Must specify a "count" setting!'

        assert isinstance(self.count, int), 'Setting "count" must be a number!'
        if "reuse_accounts" in self.dict:
            assert isinstance(
                self.reuse_accounts, bool
            ), 'Setting "reuse_accounts" must be boolean!'

        if "restore_snapshot" in self.dict:
            assert isinstance(
                self.restore_snapshot, bool
            ), 'Setting "restore_snapshot" must be boolean!'

        if self.restore_snapshot:
            assert (
                self.reuse_accounts
            ), 'Snapshot restoration requires "reuse_accounts" to be enabled!'

        if self.node_options:
            msg = (
                "node_options must be a dictionary of integer node-ids "
                "to a dictionary of node options"
            )
            assert all(isinstance(k, int) for k in self.node_options.keys()), msg
            assert all(isinstance(v, dict) for v in self.node_options.values()), msg

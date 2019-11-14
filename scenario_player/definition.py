from __future__ import annotations

import pathlib

import structlog
import yaml

from scenario_player.constants import GAS_LIMIT_FOR_TOKEN_CONTRACT_CALL
from scenario_player.utils.configuration import (
    NodesConfig,
    ScenarioConfig,
    SettingsConfig,
    SPaaSConfig,
    TokenConfig,
)

log = structlog.get_logger(__name__)


class ScenarioDefinition:
    """Interface for a Scenario `.yaml` file.

    Takes care of loading the yaml from the given `yaml_path`, and validates
    its contents.
    """

    def __init__(self, yaml_path: pathlib.Path, data_path: pathlib.Path) -> None:
        self.path = yaml_path
        with yaml_path.open() as f:
            self._loaded = yaml.safe_load(f)
        self.token = TokenConfig(self._loaded, data_path.joinpath("token.info"))
        deploy_token = self.token.address is None
        self.nodes = NodesConfig(self._loaded, environment="development" if deploy_token else None)
        self.settings = SettingsConfig(self._loaded)
        self.scenario = ScenarioConfig(self._loaded)
        self.spaas = SPaaSConfig(self._loaded)

        self.gas_limit = GAS_LIMIT_FOR_TOKEN_CONTRACT_CALL * 2

    @property
    def name(self) -> str:
        """Return the name of the scenario file, sans extension."""
        return self.path.stem

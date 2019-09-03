from __future__ import annotations

import pathlib

import structlog
import yaml

from scenario_player.constants import GAS_LIMIT_FOR_TOKEN_CONTRACT_CALL
from scenario_player.exceptions.config import InsufficientMintingAmount
from scenario_player.utils.configuration import (
    NodesConfig,
    ScenarioConfig,
    SettingsConfig,
    SPaaSConfig,
    TokenConfig,
)

log = structlog.get_logger(__name__)


class ScenarioYAML:
    """Interface for a Scenario `.yaml` file.

    Takes care of loading the yaml from the given `yaml_path`, and validates
    its contents.
    """

    def __init__(self, yaml_path: pathlib.Path, data_path: pathlib.Path) -> None:
        self.path = yaml_path
        with yaml_path.open() as f:
            self._loaded = yaml.safe_load(f)
        self.nodes = NodesConfig(self._loaded)
        self.settings = SettingsConfig(self._loaded)
        self.scenario = ScenarioConfig(self._loaded)
        self.token = TokenConfig(self._loaded, data_path.joinpath("token.info"))
        self.spaas = SPaaSConfig(self._loaded)
        self.validate()

        self.gas_limit = GAS_LIMIT_FOR_TOKEN_CONTRACT_CALL * 2

    @property
    def name(self) -> str:
        """Return the name of the scenario file, sans extension."""
        return self.path.stem

    def validate(self):
        """Validate cross-config section requirements of the scenario.

        :raises InsufficientMintingAmount:
        If token.min_balance < settings.services.udc.token.max_funding
        """

        # FIXME: This check seems to make no sense. The scenario token should be independent of the
        #        UDC token @nlsdfnbch
        # Check that the amount of minted tokens is >= than the amount of deposited tokens
        # try:
        #     assert self.token.min_balance >= self.settings.services.udc.token.max_funding
        # except AssertionError:
        #     raise InsufficientMintingAmount

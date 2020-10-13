import pathlib
from dataclasses import asdict

import jinja2
import structlog
import yaml

from scenario_player.utils.configuration.nodes import NodesConfig
from scenario_player.utils.configuration.scenario import ScenarioConfig
from scenario_player.utils.configuration.settings import (
    EnvironmentConfig,
    SettingsConfig,
)
from scenario_player.utils.configuration.token import TokenConfig

log = structlog.get_logger(__name__)


class ScenarioDefinition:
    """Interface for a Scenario `.yaml` file.

    Takes care of loading the yaml from the given `yaml_path`, and validates
    its contents.
    """

    def __init__(
        self,
        yaml_path: pathlib.Path,
        data_path: pathlib.Path,
        environment: EnvironmentConfig,
    ) -> None:
        self._scenario_dir = None
        self.path = yaml_path
        # Use the scenario file as jinja template and only parse the yaml, afterwards.
        with yaml_path.open() as f:
            yaml_template = jinja2.Template(f.read(), undefined=jinja2.StrictUndefined)
            rendered_yaml = yaml_template.render(**asdict(environment))
            self._loaded = yaml.safe_load(rendered_yaml)

        self.settings = SettingsConfig(self._loaded, environment)
        self.settings.sp_root_dir = data_path
        self.token = TokenConfig(self._loaded, self.scenario_dir.joinpath("token.info"))
        deploy_token = self.token.address is None
        self.nodes = NodesConfig(self._loaded, environment="development" if deploy_token else None)
        self.scenario = ScenarioConfig(self._loaded)

        # If the environment sets a list of matrix servers, the nodes must not
        # choose other servers, so let's set the first server from the list as
        # default.
        self.nodes.dict["default_options"]["matrix-server"] = environment.matrix_servers[0]
        self.nodes.dict["default_options"]["environment-type"] = environment.environment_type

    @property
    def name(self) -> str:
        """Return the name of the scenario file, sans extension."""
        return self.path.stem

    @property
    def scenario_dir(self) -> pathlib.Path:
        if not self._scenario_dir:
            self._scenario_dir = self.settings.sp_scenario_root_dir.joinpath(self.name)
            assert self._scenario_dir
            self._scenario_dir.mkdir(exist_ok=True, parents=True)
        return self._scenario_dir

    @property
    def snapshot_dir(self) -> pathlib.Path:
        snapshot_dir = self.scenario_dir.joinpath("snapshot")
        snapshot_dir.mkdir(parents=True, exist_ok=True)
        return snapshot_dir

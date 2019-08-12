from typing import Any, Dict, Tuple

import structlog

from scenario_player.exceptions.config import ScenarioConfigurationError
from scenario_player.utils.configuration.base import ConfigMapping

log = structlog.get_logger(__name__)


class ScenarioConfig(ConfigMapping):
    """Thin wrapper class around the "scenario" setting section of a loaded scenario .yaml file.

    The configuration will automatically be checked for
    critical errors, such as missing or mutually exclusive keys.

    Example scenario yaml::

        >my_scenario.yaml
        version: 2
        ...
        scenario:
          serial: # Root task
            # Root config
            tasks:
              - ...
    """

    CONFIGURATION_ERROR = ScenarioConfigurationError

    def __init__(self, config: dict) -> None:
        super(ScenarioConfig, self).__init__(config.get("scenario") or {})
        self.validate()

    def validate(self):
        self.assert_option(self.dict, "Must specify 'scenario' setting section!")
        self.assert_option(
            len(self) == 1,
            "Multiple tasks sections defined in scenario configuration! Must be only one!",
        )

    @property
    def root_task(self) -> Tuple[str, Any]:
        """Return the scenario's root task configuration as a tuple.

        The tuple contains the name of the task, as well as the config for it.

        The root task is the top-level task defined in the 'scenario' key,
        and typically is one of 'serial' or 'parallel', although this is not
        a requirement.

        The scenario runner takes care of recursively accessing all sub-tasks
        of the roo task.
        """
        root_task_tuple, = self.items()
        return root_task_tuple

    @property
    def root_config(self) -> Dict:
        """Return the root task config for this scenario's root task."""
        _, root_task_config = self.root_task
        return root_task_config

    @property
    def root_class(self):
        """Return the Task class type configured for the scenario root task."""
        from scenario_player.tasks.base import get_task_class_for_type

        root_task_type, _ = self.root_task

        task_class = get_task_class_for_type(root_task_type)
        return task_class

import pytest

from scenario_player.exceptions.config import ScenarioConfigurationError
from scenario_player.tasks.execution import ParallelTask, SerialTask
from scenario_player.utils.configuration.base import ConfigMapping
from scenario_player.utils.configuration.scenario import ScenarioConfig


class TestScenarioConfig:
    def test_is_subclass_of_config_mapping(self, minimal_yaml_dict):
        assert isinstance(ScenarioConfig(minimal_yaml_dict), ConfigMapping)

    @pytest.mark.parametrize(
        "task_name, expected_class", [("serial", SerialTask), ("parallel", ParallelTask)]
    )
    def test_class_loads_root_task_type_correctly(
        self, task_name, expected_class, minimal_yaml_dict
    ):
        minimal_yaml_dict["scenario"][task_name] = {}
        config = ScenarioConfig(minimal_yaml_dict)
        assert config.root_class == expected_class

    @pytest.mark.parametrize("root_task_key", ["serial", "parallel", "whatever"])
    def test_class_returns_root_config_correctly_regardless_of_root_task_name(
        self, root_task_key, minimal_yaml_dict
    ):
        injected_task_config = {"foo": "bar"}
        minimal_yaml_dict["scenario"] = {root_task_key: injected_task_config}
        config = ScenarioConfig(minimal_yaml_dict)
        assert config.root_config == injected_task_config

    def test_missing_required_key_raises_configuration_error(self, minimal_yaml_dict):
        minimal_yaml_dict.pop("tasks")
        with pytest.raises(ScenarioConfigurationError):
            ScenarioConfig(minimal_yaml_dict)

    def test_instantiating_with_an_empty_dict_raises_configuration_error(self):
        with pytest.raises(ScenarioConfigurationError):
            ScenarioConfig({})

    def test_defining_multiple_root_tasks_raises_configuration_error(self, minimal_yaml_dict):
        minimal_yaml_dict["scenario"]["second_root"] = {}
        with pytest.raises(ScenarioConfigurationError):
            ScenarioConfig(minimal_yaml_dict)

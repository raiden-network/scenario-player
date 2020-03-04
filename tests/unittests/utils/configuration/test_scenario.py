import pytest

from scenario_player.exceptions.config import ScenarioConfigurationError
from scenario_player.utils.configuration.base import ConfigMapping
from scenario_player.utils.configuration.scenario import ScenarioConfig


class TestScenarioConfig:
    def test_is_subclass_of_config_mapping(self, minimal_definition_dict):
        """The class is a subclass of :class:`ConfigMapping`."""
        assert isinstance(ScenarioConfig(minimal_definition_dict), ConfigMapping)

    @pytest.mark.xfail
    def test_class_loads_root_task_type_correctly(self, minimal_definition_dict):
        """Root tasks are checked for validity when accessing the
        :attr:`ScenarionConfig.root_class` attirbute."""
        task_name = "serial", "parallel"
        minimal_definition_dict["scenario"] = {task_name: {}}
        config = ScenarioConfig(minimal_definition_dict)  # noqa
        self.fail("Not testable due to cyclic import issue!")  # type: ignore
        # assert config.root_class == get_task_class_for_type()

    @pytest.mark.parametrize("root_task_key", ["serial", "parallel", "whatever"])
    def test_class_returns_root_config_correctly_regardless_of_root_task_name(
        self, root_task_key, minimal_definition_dict
    ):
        """:attr:`ScenarioConfig.root_config` returns config without checking
        task_name validity."""
        injected_task_config = {"foo": "bar"}
        minimal_definition_dict["scenario"] = {root_task_key: injected_task_config}
        config = ScenarioConfig(minimal_definition_dict)
        assert config.root_config == injected_task_config

    def test_missing_required_key_raises_configuration_error(self, minimal_definition_dict):
        """Missing required keys in the config dict raises a ScenarioConfigurationError."""
        minimal_definition_dict["scenario"].pop("serial")
        with pytest.raises(ScenarioConfigurationError):
            ScenarioConfig(minimal_definition_dict)

    def test_instantiating_with_an_empty_dict_raises_configuration_error(self):
        """Passing the ScenarioConfig class an empty dict is not allowed."""
        with pytest.raises(ScenarioConfigurationError):
            ScenarioConfig({})

    def test_defining_multiple_root_tasks_raises_configuration_error(
        self, minimal_definition_dict
    ):
        """Defining multiple root tasks raises a :exc:`ScenarioConfigurationError`."""
        minimal_definition_dict["scenario"]["second_root"] = {}
        with pytest.raises(ScenarioConfigurationError):
            ScenarioConfig(minimal_definition_dict)

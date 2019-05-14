import json

from unittest import mock

import pytest

from scenario_player.services.common.factories import construct_flask_app


@pytest.fixture
def TEST_CONFIG_DICT():
    return {
        'TESTING': True,
        'ICE_CREAM_FLAVOR': 'VANILLA',
    }


@pytest.fixture
def TEST_CONFIG_FILE(tmp_path):
    config_path = tmp_path.joinpath('config.py')
    config_path.touch()
    with config_path.open('w') as f:
        f.write('TESTING = False\n')
        f.write('ICE_CREAM_FLAVOR = "CHOCOLATE"\n')

    return str(config_path)


class MockConfig:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self.from_mapping_called = False
        self.from_mapping_call_count = 0
        self.from_mapping_called_with = []
        self.from_pyfile_called = False
        self.from_pyfile_call_count = 0
        self.from_pyfile_called_with = []

    def from_mapping(self, *args, **kwargs):
        self.from_mapping_called = True
        self.from_mapping_call_count += 1
        self.from_mapping_called_with += [[args, kwargs]]

    def from_pyfile(self, *args, **kwargs):
        self.from_pyfile_called = True
        self.from_pyfile_call_count += 1
        self.from_pyfile_called_with = [args, kwargs]


class MockApp:

    def __init__(self, *args, **kwargs):
        self.config = MockConfig()

    def register_blueprint(self, *args, **kwargs):
        pass


class TestConstructFlaskApp:

    @pytest.mark.parametrize('test_config', [None, {'TESTING': True}], ids=['With Test Config', 'Without Test Config'])
    @pytest.mark.parametrize('values', [{'SECRET_KEY': 'dev', 'DATABASE': 'default'}, {}], ids=['defaults', 'overrides'])
    def test_constructor_always_creates_expected_config_settings_regardless_of_test_config(self, values, test_config):
        constructed_app = construct_flask_app(test_config=test_config)
        for key, value in values.items():
            assert constructed_app.config.get(key) == value

    def test_test_config_overwrites_app_configs(self):
        config = {"DATABASE": 'custom_db', 'SECRET_KEY': 'banana pie'}
        app = construct_flask_app(test_config=config)
        for key, value in config.items():
            assert app.config.get(key) == value

    @mock.patch('scenario_player.services.common.factories.flask.Flask.register_blueprint')
    def test_registers_each_blueprint_passed_to_it(self, mock_register):
        blueprints = [object() for i in range(6)]
        construct_flask_app(*blueprints)
        assert mock_register.called

        for obj in blueprints:
            mock_register.assert_any_call(obj)

    def test_loads_config_from_file_if_no_test_config_specified(self, TEST_CONFIG_FILE):

        app = construct_flask_app(config_file=TEST_CONFIG_FILE)
        assert app.config.get('TESTING') is False
        assert app.config.get('ICE_CREAM_FLAVOR') == 'CHOCOLATE'

    def test_loads_config_from_test_config_instead_of_file_if_test_config_specified(self, TEST_CONFIG_DICT, TEST_CONFIG_FILE):

        app = construct_flask_app(test_config=TEST_CONFIG_DICT, config_file=TEST_CONFIG_FILE)
        for key, value in TEST_CONFIG_DICT.items():
            assert app.config.get(key) == value

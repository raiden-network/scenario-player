import pytest

from raiden.scenario_player.services import (
    create_release_service,
    create_node_service,
    create_keystore_service,
    create_scenario_service,
    create_runner_service,
)
from raiden.scenario_player.services.utils.testing import TestRedis


CONSTRUCTORS = {
    'node': create_node_service,
    'releases': create_release_service,
    'keystore': create_keystore_service,
    'scenario': create_scenario_service,
    'runner': create_runner_service,
}


def create_test_app(service_name, **additional_config_kwargs):
    config = {'TESTING': True, 'DATABASE': service_name}
    config.update(additional_config_kwargs)
    app = CONSTRUCTORS[service_name](config)

    return app


@pytest.fixture
def node_service_app():
    return create_test_app('node')


@pytest.fixture
def node_service_client(node_service_app):
    yield node_service_app.test_client()
    TestRedis(None).pop('node')


@pytest.fixture
def release_service_app():
    return create_test_app('releases')


@pytest.fixture
def release_service_client(release_service_app):
    yield release_service_app.test_client()
    TestRedis(None).pop('releases')


@pytest.fixture
def keystore_service_app():
    return create_test_app('keystore')


@pytest.fixture
def keystore_service_client(keystore_service_app):
    yield keystore_service_app.test_client()
    TestRedis(None).pop('keystore')


@pytest.fixture
def scenario_service_app():
    return create_test_app('scenario')


@pytest.fixture
def scenarion_service_client(scenario_service_app):
    yield scenario_service_app.test_client()
    TestRedis(None).pop('scenario')


@pytest.fixture
def runner_service_app():
    return create_test_app('runner')


@pytest.fixture
def scenarion_service_client(runner_service_app):
    yield scenario_service_app.test_client()
    TestRedis(None).pop('runner')

import os
import tempfile

import pytest

from raiden.scenario_player.services import create_release_service, create_node_service, create_keystore_service, create_scenario_service
from flaskr import create_app
from flaskr.db import get_db, init_db

SQL_SETUPS = {}
for setup_name in ('node', 'releases', 'scenario', 'keystore'):
    with open(os.path.join(os.path.dirname(__file__), f'{setup_name}.sql'), 'rb') as f:
        SQL_SETUPS[setup_name] = f.read().decode('utf8')


CONSTRUCTORS = {
    'node': create_node_service,
    'releases': create_release_service,
    'keystore': create_keystore_service,
    'scenario': create_scenario_service,
}


def create_test_app(server_name, **additional_config_kwargs):
    with tempfile.TemporaryFile() as db_fp:
        config = {'TESTING': True, 'DATABASE': db_fp.name}
        config.update(additional_config_kwargs)
        app = CONSTRUCTORS[server_name](config)

        # Setup database
        with app.app_context():
            app.init_db()
            get_db().executescript(SQL_SETUPS[server_name])
        return app


@pytest.fixture
def node_manager_app():
    return create_app('node')


@pytest.fixture
def node_manager_client(node_manager_app):
    return node_manager_app.test_client()


@pytest.fixture
def release_manager_app():
    return create_app('releases')


@pytest.fixture
def release_manager_client(release_manager_app):
    return release_manager_app.test_client()


@pytest.fixture
def keystore_manager_app():
    return create_app('keystore')


@pytest.fixture
def keystore_manager_client(keystore_manager_app):
    return keystore_manager_app.test_client()


@pytest.fixture
def scenario_manager_app():
    return create_app('scenario')


@pytest.fixture
def scenarion_manager_client(scenario_manager_app):
    return scenario_manager_app.test_client()

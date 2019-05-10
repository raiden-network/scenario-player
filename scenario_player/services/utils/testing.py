import json
import os
import tempfile
from collections.abc import MutableMapping

from scenario_player.services import (
    create_release_service,
    create_node_service,
    create_keystore_service,
    create_scenario_service,
)


class TestRedis(MutableMapping):
    """Simple Mock for unit-testing services accessing REDIS instances.

    Beware that this is NOT Thread Safe!
    Concurrent access is NOT supported!
    """
    DB = {}

    def __init__(self, table, *args, encoding_options=None, decoding_options=None, **kwargs):
        self.table = table
        self.encoding_options = encoding_options.items()
        self.decoding_options = decoding_options.items()
        self.args = args
        self.kwargs = kwargs

    def __getitem__(self, item):
        return self.DB.__getitem__(item)

    def __setitem__(self, key, value):
        return self.DB.__setitem__(key, value)

    def __iter__(self):
        return iter(self.DB)

    def __len__(self):
        return len(self.DB)

    def __delitem__(self, key):
        return super(TestRedis, self).__delitem__(key)

    def tget(self, key, *args, **decode_kwargs):
        decode_ops = dict(self.decoding_options)
        decode_ops.update(decode_kwargs)
        return self.get_json(self.table, key, *args, **decode_ops)

    def tset(self, key, value, **encode_kwargs):
        encode_ops = dict(self.encoding_options)
        enccode_ops.update(encode_kwargs)
        return self.set_json(self.table, key, value, **encode_ops)

    def set_json(self, table, key, value, **encode_kwargs):
        json_string = json.dumps(value, **encode_kwargs)
        self.__setitem__(table, {key: json_string})

    def get_json(self, table, key, *get_args, **decode_kwargs):
        json_string = self.__getitem__(table, key)
        decoded = json.loads(json_string, **decode_kwargs)
        return decoded

    def save(self):
        pass


# Database configuration for specific test setups.
TEST_DB_SETUPS = {}
for setup_name in ('node', 'releases', 'scenario', 'keystore', 'full'):
    with open(os.path.join(os.path.dirname(__file__), f'{setup_name}.json'), 'rb') as f:
        TEST_DB_SETUPS[setup_name] = json.load(f)


CONSTRUCTORS = {
    'node': create_node_service,
    'releases': create_release_service,
    'keystore': create_keystore_service,
    'scenario': create_scenario_service,
}


def create_test_app(server_name, **additional_config_kwargs):
    """Create a test app instance for unit-tests."""
    with tempfile.TemporaryFile() as db_fp:
        config = {'TESTING': True, 'DATABASE': db_fp.name}
        config.update(additional_config_kwargs)
        app = CONSTRUCTORS[server_name](config)

        # Setup database
        with app.app_context():
            get_db().executescript(TEST_DB_SETUPS[server_name])
        return app

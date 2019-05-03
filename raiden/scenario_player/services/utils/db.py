import json

from flask import current_app
from redis import Redis


class JSONRedis(Redis):
    def set_json(self, table, key, value, **encode_kwargs):
        """Store the given `value` in `table` under `key`.

        The `value` must be JSON-serializable, as it will be converted to a
        JSON-encoded string.

        `encode_kwargs` are passed to :func:`json.dumps`.
        """
        json_string = json.dumps(value, **encode_kwargs)
        self.hmset(table, {key: json_string})

    def get_json(self, table, key, *get_args, **decode_kwargs):
        """Return the value given at `key` in `table`.

        The value is decoded into a python object before it's returned.

        `get_args` are passed to :meth:`redis.Redis.get`.
        `decode_kwargs` are passed to :func:`json.loads`.
        """
        json_string = self.hmget(table, key, *get_args)
        decoded = json.loads(json_string, **decode_kwargs)
        return decoded


def get_db():
    """Get a connection object for the dataabase.

    If the config's `TESTING` setting is truthy, we return a mock connection.
    Otherwise, we return the real deal.
    """
    if 'db' not in g:
        if current_app.config.get('TESTING', False):
            g.db = TestRedis()
        else:
            g.db = JSONRedis()

    return g.db


def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.save()

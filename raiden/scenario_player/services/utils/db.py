import json
import uuid

from flask import current_app
from redis import Redis


class JSONRedis(Redis):
    """Extension around :cls:`redis.Redis`, taking care of storing python objects as
    JSON-encoded strings.

    :param table: The default table to store key-value pairs at.
    :param encoding_options:
        Default options to pass :func:`json.dumps` when setting a key-value pair.
    :param decoding_options:
        Default options to pass :func:`json.loads` when fetching a key-value pair.
    """
    def __init__(self, table, *args, encoding_options=None, decoding_options=None,  **kwargs):
        self.table = table
        self.encoding_options = encoding_options.items()
        self.decoding_options = decoding_options.items()
        super().__init__(*args, **kwargs)

    def tset(self, key, value, **kwargs):
        """Set the `value` at given `key` in the default `table`.

        The default table is stored at the instance's :attr:`.table` attribute.
        """
        return self.set_json(self.table, key, value, **kwargs)

    def tget(self, key, *args, **kwargs):
        """Get the `value` at given `key` in the default `table`.

        The default table is stored at the instance's :attr:`.table` attribute.
        """
        return self.get_json(key, value, *args, **kwargs)

    def set_json(self, table, key, value, **encode_kwargs):
        """Store the given `value` in `table` under `key`.

        The `value` must be JSON-serializable, as it will be converted to a
        JSON-encoded string.

        `encode_kwargs` are passed to :func:`json.dumps`.
        """
        encode_options = dict(self.encoding_options)
        encode_options.update(encode_kwargs)
        json_string = json.dumps(value, **encode_options)
        self.hmset(table, {key: json_string})

    def get_json(self, table, key, *get_args, **decode_kwargs):
        """Return the value given at `key` in `table`.

        The value is decoded into a python object before it's returned.

        `get_args` are passed to :meth:`redis.Redis.get`.
        `decode_kwargs` are passed to :func:`json.loads`.
        """
        decode_options = dict(self.decoding_options)
        decode_options.update(decode_kwargs)
        json_string = self.hmget(table, key, *get_args)
        decoded = json.loads(json_string, **decode_options)
        return decoded


def get_db():
    """Get a connection object for the database.

    If the config's `TESTING` setting is truthy, we return a mock connection.
    Otherwise, we return the real deal.

    If you do not specify a  redis table name in the `DATABASE` field of
    the app's config, we'll generate a new table name using :func:`uuid.uuid4`.

    Additionally, the table will be dropped once the application shuts down.

    ..NOTE::

        While we do not persist data in auto-generated tables (using :func:`uuid.uuid4`),
        data that is written to **other tables than the one stored at :attr:`.table`**
        may be persistent - depending on the nature of the table the data was written to.

        The same holds true the other way around - data is persisted if a table is
        explicitly stated: however, this guarantee only regards the internally
        set table.

        It is therefore recommended to either

            **a) always specify a table name**
                Data is persistently stored, even after the app shuts down.

        or
            **b) never specify a table name**
                All data will be dropped once the application shuts down.

    """
    db_name = current_app.config.get('DATABASE', False)
    if not db_name:
        # Generate a table name to store data under.
        db_name = uuid.uuid4()
        current_app.config['PERSIST_DB'] = False
        current_app.config['DATABASE'] = db_name

    if 'db' not in g:
        if current_app.config.get('TESTING', False):
            # Import the test db class on the fly, to avoid circular import fuck-ups.
            from raiden.scenario_player.services.utils.testing import TestRedis
            g.db = TestRedis(db_name)
        else:
            g.db = JSONRedis(db_name)

    return g.db


def close_db(e=None):
    """Close the database connection, saving its state if applicable."""
    db = g.pop('db', None)
    if db is not None:
        if not current_app.config.get('PERSIST_DB', True):
            db.delete(db.table)
        db.save()


import copy
import json
from typing import Dict, MutableMapping, Optional, Union

from flask import current_app, g
from redis import Redis

from scenario_player.exceptions.db import CorruptedDBEntry

DecodedJSONDict = Dict[str, Union[dict, list, str, int, float, bool, None]]
JSONEncodableDict = Dict[str, Union[dict, list, tuple, str, int, float, bool, None]]
RedisTestInstance = MutableMapping


class JSONRedis(Redis):
    """Extension around :cls:`redis.Redis`, taking care of storing python objects as
    JSON-encoded strings.

    :param table: The default table to store key-value pairs at.
    :param encoding_options:
        Default options to pass :func:`json.dumps` when setting a key-value pair.
    :param decoding_options:
        Default options to pass :func:`json.loads` when fetching a key-value pair.
    """

    def __init__(
        self,
        table: str,
        *args,
        encoding_options: Optional[dict] = None,
        decoding_options: Optional[dict] = None,
        **kwargs,
    ):
        self.default_table = table
        self.encoding_options = encoding_options or {}
        self.decoding_options = decoding_options or {}
        super().__init__(*args, **kwargs)

    def tset(self, key: str, value: JSONEncodableDict, **encode_kwargs):
        """Set the `value` at given `key` in the default `table`.

        The default table is stored at the instance's :attr:`.table` attribute.
        """
        return self.set_json(self.default_table, key, value, **encode_kwargs)

    def set_json(self, table: str, key: str, value: JSONEncodableDict, **encode_kwargs):
        """Store the given `value` in `table` under `key`.

        The `value` must be JSON-serializable, as it will be converted to a
        JSON-encoded string.

        `encode_kwargs` are passed to :func:`json.dumps`.
        """
        encode_options = copy.deepcopy(self.encoding_options)
        encode_options.update(encode_kwargs)
        json_string: str = json.dumps(value, **encode_options)
        self.hmset(table, {key: json_string})

    def tget(self, key, *get_args, **decode_kwargs) -> DecodedJSONDict:
        """Get the `value` at given `key` in the default `table`.

        The default table is stored at the instance's :attr:`.table` attribute.

        :raises CorruptedDBEntry:
            if downstream was not able to decode the string stored at ``key``
            of :attr:``.default_table`` as JSON.
        """
        try:
            return self.get_json(self.default_table, key, *get_args, **decode_kwargs)
        except json.JSONDecodeError as e:
            raise CorruptedDBEntry(table=self.default_table, key=key) from e

    def get_json(self, table: str, key: str, *get_args, **decode_kwargs) -> DecodedJSONDict:
        """Return the value given at `key` in `table`.

        The value is decoded into a python object before it's returned.

        `get_args` are passed to :meth:`redis.Redis.get`.
        `decode_kwargs` are passed to :func:`json.loads`.
        """
        decode_options = copy.deepcopy(self.decoding_options)
        decode_options.update(decode_kwargs)
        json_string: str = self.hmget(table, key, *get_args)
        decoded = json.loads(json_string, **decode_options)
        return decoded


def get_db() -> Union[JSONRedis, RedisTestInstance]:
    """Get a connection object for the database.

    If the config's `TESTING` setting is truthy, we return a mock connection.
    Otherwise, we return the real deal.

    If you do not specify a  redis table name in the `DATABASE` field of
    the app's config, the table ``default`` will be used.

    Data is persisted by default, unless ``PERSIST_DB=False`` is set in the app's
    config.
    """
    db_name = current_app.config.get("DATABASE", "default")
    if "db" not in g:
        if current_app.config.get("TESTING", False):
            # Import the test db class on the fly, to avoid circular import fuck-ups.
            from scenario_player.services.utils.testing import TestRedis

            g.db = TestRedis(db_name)
        else:
            g.db = JSONRedis(db_name)

    return g.db


def close_db(e=None) -> None:
    """Close the database connection.

    If there is no `'db'` key in the thread-local :var:`flask.g`, this is a no-op.

    If  `PERSIST_DB=False` in the app's config or the key-value pair is absent entirely,
    we explicitly drop the database.

    If `TESTING=False` in the app's config or the key-value pair is absent entirely,
    we explicitly drop the database.

    If a `'db'` key existed, we call the `save()` method on the object returned
    by accessing it from the thread-local :var:`flask.g`.
    """
    db = g.pop("db", None)
    if db is not None:
        if not current_app.config.get("PERSIST_DB", True) or current_app.config.get(
            "TESTING", False
        ):
            db.delete(db.table)
        db.save()

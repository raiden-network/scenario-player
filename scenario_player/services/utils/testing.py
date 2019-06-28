from typing import Dict


class TestRedis:
    """Simple Mock for unit-testing services accessing REDIS instances.

    Beware that this is NOT Thread Safe!
    Concurrent access is NOT supported!
    """

    #: Our mock redis server. Will be a a dict of dicts, where each first-level
    #: dict will act as a redis `table`. Second-level dicts will have str keys and
    #: their values will be JSON-encoded strings.
    DB = {}

    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

    def hmset(self, table: str, key_value: Dict[str, str], *args, **kwargs) -> None:
        current = self.DB.get(table, {})
        current.update(key_value)
        self.DB[table] = current

    def hmget(self, table: str, key: str, *args, **kwargs) -> str:
        return self.DB.get(table, {}).get(key)

    def save(self):
        """Pretend to save our DB. This is a no-op."""

    def delete(self, *tables):
        """Delete a top-level key."""
        for table in tables:
            self.DB.pop(table, None)
import json
from collections.abc import MutableMapping
from typing import Any, Optional


class TestRedis(MutableMapping):
    """Simple Mock for unit-testing services accessing REDIS instances.

    Beware that this is NOT Thread Safe!
    Concurrent access is NOT supported!
    """

    DB = {}

    def __init__(self, table: str, *args, encoding_options: Optional[dict]=None, decoding_options: Optional[dict]=None, **kwargs):
        self.table = table
        self.encoding_options = (encoding_options or {}).items()
        self.decoding_options = (decoding_options or {}).items()
        self.args = args
        self.kwargs = kwargs

    def __getitem__(self, item: str):
        return self.DB.__getitem__(item)

    def __setitem__(self, key: str, value: Any):
        return self.DB.__setitem__(key, value)

    def __iter__(self):
        return iter(self.DB)

    def __len__(self):
        return len(self.DB)

    def __delitem__(self, key: str):
        return super(TestRedis, self).__delitem__(key)

    def tget(self, key: str, *args, **decode_kwargs) -> Any:
        decode_ops = dict(self.decoding_options)
        decode_ops.update(decode_kwargs)
        return self.get_json(self.table, key, *args, **decode_ops)

    def tset(self, key: str, value: Any, **encode_kwargs) -> None:
        encode_ops = dict(self.encoding_options)
        encode_ops.update(encode_kwargs)
        return self.set_json(self.table, key, value, **encode_ops)

    def set_json(self, table: str, key: str, value: Any, **encode_kwargs) -> None:
        json_string = json.dumps(value, **encode_kwargs)
        self.__setitem__(table, {key: json_string})

    def get_json(self, table: str, key: str, *_, **decode_kwargs) -> Any:
        json_string = self.__getitem__(table, key)
        decoded = json.loads(json_string, **decode_kwargs)
        return decoded

    def save(self):
        pass

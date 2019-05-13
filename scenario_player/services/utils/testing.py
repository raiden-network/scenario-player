import json

from collections.abc import MutableMapping


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

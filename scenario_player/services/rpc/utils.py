import hashlib
import hmac
from collections.abc import Mapping
from typing import Tuple, Union

from flask import abort, current_app
from web3 import Web3
from werkzeug.routing import BaseConverter

from raiden.network.rpc.client import JSONRPCClient


class RPCClientLoader(BaseConverter):
    """Url Variable converter to automatically load rpc client instances using their ids.

    This converter must first be registered with the app before it can be used::


        from flask import Flask

        app = Flask(__name__)

        from .util import ListConverter

        app.url_map.converters['rpc-client'] = RPCClientLoader

    You can then use it as follows in route decorators::

        from raiden.network.rpc.client import JSONRPCClient

        @app.route('/rpc/client/<client_id:rpc-client>')
        def converter_demo(client):
            assert isinstance(client, JSONRPCClient)
            return "Converted"
    """

    def to_python(self, value):
        try:
            return current_app.config["rpc-client"][value]
        except KeyError:
            abort(400, description=value)

    def to_url(self, value):
        for k, v in current_app.config["rpc-client"].items():
            if value == v:
                return k


def generate_hash_key(chain_url: str, privkey: bytes):
    """Generate a key using the `chain_url` and `privkey` args and the :mod:`hmac` library."""
    k = hmac.new(privkey, chain_url.encode("UTF-8"), hashlib.sha256)
    return k.hexdigest()


class RPCRegistry(Mapping):
    """Custom mapping, allowing dynamic creation of JSONRPCClient instances.

    It does not allow assigning new instances directly. However, popping
    instances is allowed.
    """

    def __init__(self):
        self.dict = {}

    def __getitem__(
        self, item: Union[str, Tuple[str, str], Tuple[str, str, str]]
    ) -> Tuple[JSONRPCClient, str]:
        try:
            return self.dict[item], item
        except KeyError:
            if isinstance(item, tuple) and len(item) in range(2, 4):
                url, privkey, *strategy = item
                # Strategy may be an empty list if the tuple was only 2 items long.
                strategy = strategy or "fast"

                key = generate_hash_key(url, privkey)
                if key not in self.dict:
                    try:
                        self.dict[key] = JSONRPCClient(
                            Web3(url), privkey=privkey, gas_price_strategy=strategy
                        )
                    except ValueError as e:
                        abort(400, description=str(e))
                return self.dict[key], key
            abort(404, description=f"No JSONRPCClient instance with id {item} found!")

    def __len__(self):
        return len(self.dict)

    def __iter__(self):
        return iter(self.dict)

    def pop(self, key, default=None):
        return self.dict.pop(key, default)

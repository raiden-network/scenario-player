import hashlib
import hmac
from collections.abc import Mapping
from typing import Callable, Tuple, Union

import structlog
from eth_utils import encode_hex
from web3 import HTTPProvider, Web3

from raiden.network.rpc.client import JSONRPCClient

log = structlog.getLogger(__name__)


def assign_rpc_instance_id(runner, chain_url, privkey, gas_price):
    params = {"chain_url": chain_url, "privkey": encode_hex(privkey), "gas_price": gas_price}
    resp = runner.service_session.post("spaas://rpc/client", json=params)
    client_id = resp.json()["client_id"]
    runner.definition.spaas.rpc.client_id = client_id


def generate_hash_key(chain_url: str, privkey: bytes, strategy: Callable):
    """Generate a hash key to use as `client_id`, using the :mod:`hmac` library.

    The message is the concatenation of `chain_url` plus the `__name__` attribute of the
    `strategy`.

    The `privkey` is used to sign it using `sha256`.

    The result is hexdigested before we return it.
    """
    k = hmac.new(privkey, (chain_url + strategy.__name__).encode("UTF-8"), hashlib.sha256)
    return k.hexdigest()


class RPCClient(JSONRPCClient):
    def __init__(self, chain_url, privkey, strategy):
        super(RPCClient, self).__init__(
            Web3(HTTPProvider(chain_url)),
            privkey=privkey,
            gas_price_strategy=strategy,
            block_num_confirmations=5,
        )
        self.client_id = generate_hash_key(chain_url, privkey, strategy)


class RPCRegistry(Mapping):
    """Custom mapping, allowing dynamic creation of JSONRPCClient instances.

    It does not allow assigning new instances directly. However, popping
    instances is allowed.
    """

    def __init__(self):
        self.dict = {}

    def __getitem__(self, item: Union[str, Tuple[str, str, Callable]]) -> RPCClient:
        try:
            return self.dict[item]
        except KeyError:
            if not self.is_valid_tuple(item):
                raise

            chain_url, privkey, strategy = item
            client_id = generate_hash_key(chain_url, privkey, strategy)

            if client_id not in self.dict:
                log.debug(
                    "Creating new RPC instance", chain_url=chain_url, strategy=strategy.__name__
                )
                self.dict[client_id] = RPCClient(chain_url, privkey, strategy)

            return self.dict[client_id]

    def __len__(self):
        return len(self.dict)

    def __iter__(self):
        return iter(self.dict)

    def is_valid_tuple(self, t) -> bool:
        """check if the given tuple can be used to instantiate a new RPC class."""
        try:
            chain_url, privkey, strategy = t
        except (ValueError, TypeError):
            return False
        else:
            if isinstance(chain_url, str) and isinstance(privkey, bytes) and callable(strategy):
                return True
            return False

    def pop(self, key, default=None):
        return self.dict.pop(key, default)

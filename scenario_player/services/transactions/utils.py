import hashlib
import hmac

from flask import current_app
from web3 import Web3

from raiden.network.rpc.client import JSONRPCClient


def generate_hash_key(chain_url: str, privkey: bytes):
    """Generate a key using the `chain_url` and `privkey` args and the :mod:`hmac` library."""
    k = hmac.new(privkey, chain_url.encode("UTF-8"), hashlib.sha256)
    return k.hexdigest()


def get_rpc_client(
    chain_url: str, privkey: bytes, gas_price_strategy: str, **kwargs
) -> JSONRPCClient:
    """Get the JSONRPCClient instance for the given `run_id`.

    If no :class:`JSONRPCClient` instance exists for the given `run_id`, we
    create one, store and return it.
    """
    client_key = generate_hash_key(chain_url, privkey)
    try:
        rpc_client = current_app.config["rpc-client"][client_key]
    except KeyError:
        current_app.config["rpc-client"][client_key] = JSONRPCClient(
            Web3(chain_url), privkey=privkey, gas_price_strategy=gas_price_strategy
        )
        rpc_client = current_app.config["rpc-client"][client_key]
    return rpc_client

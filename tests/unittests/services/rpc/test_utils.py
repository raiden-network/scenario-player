import hashlib
import hmac
from unittest import mock

import pytest

from scenario_player.constants import GAS_STRATEGIES
from scenario_player.services.rpc.utils import RPCClient, RPCRegistry, generate_hash_key


@pytest.mark.dependency(name="generate_hash_key_for_transactions_service")
def test_generate_hash_key_uses_shalib256_digested_hmac_hexdigests():
    url = "http://test.net"
    privkey = b"my_private_key"
    strategy = GAS_STRATEGIES["FAST"]
    expected = hmac.new(
        privkey, (url + strategy.__name__).encode("UTF-8"), hashlib.sha256
    ).hexdigest()
    assert generate_hash_key(url, privkey, strategy) == expected


class TestRPCRegistry:
    def test_class_behaves_like_immutable_dict(self, transaction_service_client):
        registry = RPCRegistry()
        with pytest.raises(TypeError):
            registry["hello"] = "goodbye"

        with pytest.raises(TypeError):
            del registry["something"]

    def test_class_implements_pop_method(self, transaction_service_client):
        assert RPCRegistry().pop("Something") is None

    @pytest.mark.parametrize(
        "invalid_key",
        argvalues=[(1,), (1, 2, 3, 4), "non-existing-id", 42.5, 20],
        ids=[
            "Item is tuple, but too short",
            "Item is tuple, but too long",
            "Item is str, but non-existing instance id",
            "Item is float",
            "Item is int",
        ],
    )
    def test_getitem_raises_keyerror(self, invalid_key):
        with pytest.raises(KeyError):
            RPCRegistry()[invalid_key]

    @pytest.mark.parametrize(
        "valid_tuple",
        argvalues=[
            ("https://test.net", b"12345678909876543211234567890098", GAS_STRATEGIES["FAST"])
        ],
        ids=["3-item-tuple"],
    )
    @mock.patch("scenario_player.services.rpc.utils.JSONRPCClient.__init__")
    def test_getitem_with_valid_tuple_creates_stores_and_returns_rpc_instance(
        self, mock_parent, valid_tuple
    ):
        registry = RPCRegistry()
        chain_url, privkey, strategy = (
            "https://test.net",
            b"12345678909876543211234567890098",
            GAS_STRATEGIES["FAST"],
        )
        expected_id = generate_hash_key(chain_url, privkey, strategy)
        # Assert the registry does not have the instance.
        with pytest.raises(KeyError):
            registry[expected_id]

        instance = registry[valid_tuple]
        assert instance.client_id == expected_id
        assert isinstance(instance, RPCClient)
        assert registry[instance.client_id] == instance

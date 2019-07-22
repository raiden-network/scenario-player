import hashlib
import hmac
from unittest import mock

import pytest
import werkzeug

from raiden.network.rpc.client import JSONRPCClient
from scenario_player.services.rpc.utils import RPCRegistry, generate_hash_key


@pytest.mark.dependency(name="generate_hash_key_for_transactions_service")
def test_generate_hash_key_uses_shalib256_digested_hmac_hexdigests():
    url = "http://test.net"
    privkey = b"my_private_key"
    expected = hmac.new(privkey, url.encode("UTF-8"), hashlib.sha256).hexdigest()
    assert generate_hash_key(url, privkey) == expected


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
        with pytest.raises(werkzeug.exceptions.NotFound):
            RPCRegistry()[invalid_key]

    @pytest.mark.parametrize(
        "valid_tuple",
        argvalues=[
            ("https://test.net", b"12345678909876543211234567890098"),
            ("https://test.net", b"12345678909876543211234567890098", "slow"),
        ],
        ids=["2-item tuple", "3-item-tuple"],
    )
    @mock.patch("scenario_player.services.rpc.utils.JSONRPCClient", autospec=True)
    def test_getitem_with_valid_tuple_creates_stores_and_returns_rpc_instance(
        self, mock_rpc_client, valid_tuple
    ):

        registry = RPCRegistry()
        chain_url, privkey, *strategy = valid_tuple
        expected_id = generate_hash_key(chain_url, privkey)
        # Assert the registry does not have the instance.
        with pytest.raises(werkzeug.exceptions.NotFound):
            registry[expected_id]

        instance, actual_id = registry[valid_tuple]
        mock_rpc_client.assert_called_once()
        assert actual_id == expected_id
        assert isinstance(instance, JSONRPCClient)
        assert registry[actual_id] == (instance, actual_id)

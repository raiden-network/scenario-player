from unittest import mock
import hashlib
import hmac
import pytest

from scenario_player.services.transactions.utils import generate_hash_key, get_rpc_client


@pytest.mark.dependency(name="generate_hash_key_for_transactions_service")
def test_generate_hash_key_uses_shalib256_digested_hmac_hexdigests():
    url = "http://test.net"
    privkey = b"my_private_key"
    expected = hmac.new(privkey, url.encode("UTF-8"), hashlib.sha256).hexdigest()
    assert generate_hash_key(url, privkey) == expected


@pytest.mark.dependency(depends=["generate_hash_key_for_transactions_service"])
@mock.patch("scenario_player.services.transactions.utils.JSONRPCClient")
class TestGetRPCClientFunc:

    @mock.patch("scenario_player.services.transactions.utils.Web3")
    def test_func_assigns_new_instance_if_client_key_does_not_exist(self, mock_web3, mock_rpc_client, transaction_service_app):
        url = "https://test.net"
        privkey = b"privkey"
        gas_price_strategy = "fast"

        client_key = generate_hash_key(url, privkey)

        mock_rpc_client.return_value = mock_rpc_client

        with transaction_service_app.app_context():
            assert transaction_service_app.config["rpc-client"] == {}

            get_rpc_client(url, privkey, gas_price_strategy)
            args, kwargs = mock_rpc_client.call_args
            assert mock_web3(url) in args
            for k, v in {"privkey": privkey, "gas_price_strategy": gas_price_strategy}.items():
                assert k in kwargs
                assert kwargs[k] == v

            assert transaction_service_app.config["rpc-client"][client_key] == mock_rpc_client

    def test_func_returns_existing_instance_if_client_key_exists(self, mock_rpc_client, transaction_service_app):
        url = "https://test.net"
        privkey = b"privkey"
        gas_price_strategy = "fast"

        client_key = generate_hash_key(url, privkey)

        mock_rpc_client.return_value = mock_rpc_client

        expected = object()

        with transaction_service_app.app_context():
            assert transaction_service_app.config["rpc-client"] == {}
            transaction_service_app.config["rpc-client"][client_key] = expected

            # Assert it's the expected object returned.
            assert get_rpc_client(url, privkey, gas_price_strategy) == expected

            # Assert the returned object is also still present in the config.
            assert transaction_service_app.config["rpc-client"][client_key] == expected

import pytest

from scenario_player.services.transactions.utils import generate_hash_key, get_rpc_client


@pytest.mark.depends(name="generate_hash_key_for_transactions_service")
def test_generate_hash_key_uses_shalib256_digested_hmac_hexdigests():
    pass
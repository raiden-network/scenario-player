import pytest
from tests.unittests.constants import NODE_ADDRESS_0, NODE_ADDRESS_1, TEST_TOKEN_ADDRESS

# TODO: Add tests for request timeouts
from tests.unittests.tasks.utils import assert_task_test, generic_task_test

from scenario_player.exceptions import (
    RESTAPIStatusMismatchError,
    ScenarioAssertionError,
    ScenarioError,
)
from scenario_player.tasks.channels import STORAGE_KEY_CHANNEL_INFO


@pytest.mark.parametrize(
    (
        "task_name",
        "task_params",
        "expected_exception",
        "expected_exception_message",
        "expected_req_method",
        "expected_req_url",
        "expected_req_body",
        "resp_code",
        "resp_json",
    ),
    argvalues=[
        pytest.param(
            "open_channel",
            {"from": 0, "to": 1},
            None,
            None,
            "PUT",
            "http://0/api/v1/channels",
            {"token_address": TEST_TOKEN_ADDRESS, "partner_address": NODE_ADDRESS_1},
            200,
            {"resp": 1},
            id="open-channel-simple",
        ),
        pytest.param(
            "open_channel",
            {"from": 0, "to": f"0x3{10:039d}"},
            None,
            None,
            "PUT",
            "http://0/api/v1/channels",
            {"token_address": TEST_TOKEN_ADDRESS, "partner_address": f"0x3{10:039d}"},
            200,
            {"resp": 1},
            id="open-channel-external-address",
        ),
        pytest.param(
            "open_channel",
            {"from": 1, "to": 0, "total_deposit": 100},
            None,
            None,
            "PUT",
            "http://1/api/v1/channels",
            {
                "token_address": TEST_TOKEN_ADDRESS,
                "partner_address": NODE_ADDRESS_0,
                "total_deposit": 100,
            },
            200,
            {"resp": 1},
            id="open-channel-w-deposit",
        ),
        pytest.param(
            "open_channel",
            {"from": 1, "to": 0, "total_deposit": 100, "settle_timeout": 501},
            None,
            None,
            "PUT",
            "http://1/api/v1/channels",
            {
                "token_address": TEST_TOKEN_ADDRESS,
                "partner_address": NODE_ADDRESS_0,
                "total_deposit": 100,
                "settle_timeout": 501,
            },
            200,
            {"resp": 1},
            id="open-channel-w-deposit-settle",
        ),
        pytest.param(
            "open_channel",
            {"from": 0, "to": 1},
            RESTAPIStatusMismatchError,
            None,
            "PUT",
            "http://0/api/v1/channels",
            {"token_address": TEST_TOKEN_ADDRESS, "partner_address": NODE_ADDRESS_1},
            409,
            {},
            id="open-channel-conflict",
        ),
        pytest.param(
            "open_channel",
            {"from": 0, "to": 1, "expected_http_status": "(2..|409)"},
            None,
            None,
            "PUT",
            "http://0/api/v1/channels",
            {"token_address": TEST_TOKEN_ADDRESS, "partner_address": NODE_ADDRESS_1},
            409,
            {"resp": 1},
            id="open-channel-conflict-expected",
        ),
        pytest.param(
            "close_channel",
            {"from": 0, "to": 1},
            None,
            None,
            "PATCH",
            f"http://0/api/v1/channels/{TEST_TOKEN_ADDRESS}/{NODE_ADDRESS_1}",
            {"state": "closed"},
            200,
            {"resp": 1},
            id="close-channel-simple",
        ),
        pytest.param(
            "deposit",
            {"from": 0, "to": 1},
            KeyError,
            None,
            None,
            None,
            None,
            None,
            None,
            id="deposit-missing-param",
        ),
        pytest.param(
            "deposit",
            {"from": 0, "to": 1, "total_deposit": 100},
            None,
            None,
            "PATCH",
            f"http://0/api/v1/channels/{TEST_TOKEN_ADDRESS}/{NODE_ADDRESS_1}",
            {"total_deposit": 100},
            200,
            {"resp": 1},
            id="deposit-simple",
        ),
        pytest.param(
            "deposit",
            {"from": 0, "to": f"0x3{10:039d}", "total_deposit": 100},
            None,
            None,
            "PATCH",
            f"http://0/api/v1/channels/{TEST_TOKEN_ADDRESS}/0x3{10:039d}",
            {"total_deposit": 100},
            200,
            {"resp": 1},
            id="deposit-simple-external-address",
        ),
        pytest.param(
            "withdraw",
            {"from": 0, "to": 1},
            KeyError,
            None,
            None,
            None,
            None,
            None,
            None,
            id="withdraw-missing-param",
        ),
        pytest.param(
            "withdraw",
            {"from": 0, "to": 1, "total_withdraw": 100},
            None,
            None,
            "PATCH",
            f"http://0/api/v1/channels/{TEST_TOKEN_ADDRESS}/{NODE_ADDRESS_1}",
            {"total_withdraw": 100},
            200,
            {"resp": 1},
            id="withdraw-simple",
        ),
        pytest.param(
            "burn",
            {"from": 0, "to": 1},
            KeyError,
            None,
            None,
            None,
            None,
            None,
            None,
            id="burn-missing-param",
        ),
        pytest.param(
            "burn",
            {"from": 0, "to": 1, "total_burn": 100},
            None,
            None,
            "PATCH",
            f"http://0/api/v1/channels/{TEST_TOKEN_ADDRESS}/{NODE_ADDRESS_1}",
            {"total_burn": 100},
            200,
            {"resp": 1},
            id="burn-simple",
        ),
        pytest.param(
            "transfer",
            {"from": 0, "to": 1},
            KeyError,
            None,
            None,
            None,
            None,
            None,
            None,
            id="transfer-missing-param",
        ),
        pytest.param(
            "transfer",
            {"from": 0, "to": 1, "amount": 1},
            None,
            None,
            "POST",
            f"http://0/api/v1/payments/{TEST_TOKEN_ADDRESS}/{NODE_ADDRESS_1}",
            {"amount": 1, "identifier": 135127100001000001},
            200,
            {"resp": 1},
            id="transfer-simple",
        ),
        pytest.param(
            "transfer",
            {"from": 0, "to": 1, "amount": 1, "identifier": "generate"},
            None,
            None,
            "POST",
            f"http://0/api/v1/payments/{TEST_TOKEN_ADDRESS}/{NODE_ADDRESS_1}",
            {"amount": 1, "identifier": 135127100001000001},
            200,
            {"resp": 1},
            id="transfer-id-generated",
        ),
        pytest.param(
            "transfer",
            {"from": 0, "to": 1, "amount": 1, "identifier": 1},
            None,
            None,
            "POST",
            f"http://0/api/v1/payments/{TEST_TOKEN_ADDRESS}/{NODE_ADDRESS_1}",
            {"amount": 1, "identifier": 1},
            200,
            {"resp": 1},
            id="transfer-id-given",
        ),
        pytest.param(
            "transfer",
            {"from": 0, "to": 1, "amount": 1, "identifier": 1, "lock_timeout": 30},
            None,
            None,
            "POST",
            f"http://0/api/v1/payments/{TEST_TOKEN_ADDRESS}/{NODE_ADDRESS_1}",
            {"amount": 1, "identifier": 1, "lock_timeout": 30},
            200,
            {"resp": 1},
            id="transfer-lock-timeout-given",
        ),
        pytest.param(
            "assert_all",
            {"from": 0},
            None,
            None,
            "GET",
            f"http://0/api/v1/channels/{TEST_TOKEN_ADDRESS}",
            {},
            200,
            {"resp": 1},
            id="assert_all-nothing",
        ),
        pytest.param(
            "assert_all",
            {"from": 0, "balances": [100, 50]},
            None,
            None,
            "GET",
            f"http://0/api/v1/channels/{TEST_TOKEN_ADDRESS}",
            {},
            200,
            [{"balance": "100"}, {"balance": "50"}],
            id="assert_all-balance-simple",
        ),
        pytest.param(
            "assert_all",
            {"from": 0, "total_deposit": [100, 50]},
            None,
            None,
            "GET",
            f"http://0/api/v1/channels/{TEST_TOKEN_ADDRESS}",
            {},
            200,
            [{"total_deposit": "100"}, {"total_deposit": "50"}],
            id="assert_all-total_deposit-simple",
        ),
        pytest.param(
            "assert_all",
            {"from": 0, "state": ["open", "closed"]},
            None,
            None,
            "GET",
            f"http://0/api/v1/channels/{TEST_TOKEN_ADDRESS}",
            {},
            200,
            [{"state": "open"}, {"state": "closed"}],
            id="assert_all-state-simple",
        ),
        pytest.param(
            "assert_all",
            {"from": 0, "balances": [100, 50]},
            ScenarioError,
            'Field "balance" is missing in at least one channel',
            "GET",
            f"http://0/api/v1/channels/{TEST_TOKEN_ADDRESS}",
            {},
            200,
            [{"balance": "100"}, {}],
            id="assert_all-balance-missing-field",
        ),
        pytest.param(
            "assert_all",
            {"from": 0, "balances": [100, 50, 30]},
            ScenarioError,
            'Assertion field "balance" has too many values.',
            "GET",
            f"http://0/api/v1/channels/{TEST_TOKEN_ADDRESS}",
            {},
            200,
            [{"balance": "100"}, {"balance": "50"}],
            id="assert_all-balance-too-many-values",
        ),
        pytest.param(
            "assert_all",
            {"from": 0, "balances": [100, 90]},
            ScenarioAssertionError,
            'Expected value "90" for field "balance" not found in any channel.',
            "GET",
            f"http://0/api/v1/channels/{TEST_TOKEN_ADDRESS}",
            {},
            200,
            [{"balance": "100"}, {"balance": "50"}],
            id="assert_all-balance-not-found",
        ),
        pytest.param(
            "assert_sum",
            {"from": 0, "balance_sum": 100},
            None,
            None,
            "GET",
            f"http://0/api/v1/channels/{TEST_TOKEN_ADDRESS}",
            {},
            200,
            [{"balance": "50"}, {"balance": "50"}],
            id="assert_sum-balance-simple",
        ),
        pytest.param(
            "assert_sum",
            {"from": 0, "total_deposit_sum": 100},
            None,
            None,
            "GET",
            f"http://0/api/v1/channels/{TEST_TOKEN_ADDRESS}",
            {},
            200,
            [{"total_deposit": "50"}, {"total_deposit": "50"}],
            id="assert_sum-total_deposit-simple",
        ),
        pytest.param(
            "assert_sum",
            {"from": 0, "state_sum": "open"},
            None,
            None,
            "GET",
            f"http://0/api/v1/channels/{TEST_TOKEN_ADDRESS}",
            {},
            200,
            [{"state": "open"}, {"state": "open"}],
            id="assert_sum-state-simple",
        ),
        pytest.param(
            "assert_sum",
            {"from": 0, "balance_sum": 100},
            ScenarioAssertionError,
            'Expected sum value "100" for channel fields "balance". Actual value: "90".',
            "GET",
            f"http://0/api/v1/channels/{TEST_TOKEN_ADDRESS}",
            {},
            200,
            [{"balance": "50"}, {"balance": "40"}],
            id="assert_sum-balance-mismatch",
        ),
        pytest.param(
            "assert_sum",
            {"from": 0, "state_sum": "open"},
            ScenarioAssertionError,
            'Expected all channels to be in "open" state.',
            "GET",
            f"http://0/api/v1/channels/{TEST_TOKEN_ADDRESS}",
            {},
            200,
            [{"state": "open"}, {"state": "closed"}],
            id="assert_sum-state-mismatch",
        ),
    ],
)
def test_channel_task(
    mocked_responses,
    api_task_by_name,
    task_name,
    task_params,
    expected_exception,
    expected_exception_message,
    expected_req_method,
    expected_req_url,
    expected_req_body,
    resp_code,
    resp_json,
):
    # See ``generic_task_test`` for an explanation of the parameters
    generic_task_test(
        mocked_responses=mocked_responses,
        api_task_by_name=api_task_by_name,
        task_name=task_name,
        task_params=task_params,
        expected_exception=expected_exception,
        expected_exception_message=expected_exception_message,
        expected_req_method=expected_req_method,
        expected_req_url=expected_req_url,
        expected_req_body=expected_req_body,
        resp_code=resp_code,
        resp_json=resp_json,
    )


# TODO: This has the same body as test_channel_task above. Can they be merged?
@pytest.mark.parametrize(
    (
        "task_name",
        "task_params",
        "expected_exception",
        "expected_exception_message",
        "expected_req_method",
        "expected_req_url",
        "expected_req_body",
        "resp_code",
        "resp_json",
    ),
    argvalues=[
        pytest.param(
            "assert",
            {"from": 0, "to": 1},
            None,
            None,
            "GET",
            f"http://0/api/v1/channels/{TEST_TOKEN_ADDRESS}/{NODE_ADDRESS_1}",
            {},
            200,
            {"resp": 1},
            id="assert-nothing",
        ),
        pytest.param(
            "assert",
            {"from": 0, "to": 1, "balance": 100},
            None,
            None,
            "GET",
            f"http://0/api/v1/channels/{TEST_TOKEN_ADDRESS}/{NODE_ADDRESS_1}",
            {},
            200,
            {"balance": "100"},
            id="assert-balance",
        ),
        pytest.param(
            "assert",
            {"from": 0, "to": 1, "balance": 100, "allow_balance_error": 1},
            None,
            None,
            "GET",
            f"http://0/api/v1/channels/{TEST_TOKEN_ADDRESS}/{NODE_ADDRESS_1}",
            {},
            200,
            {"balance": "101"},
            id="assert-balance-with-allowed-error",
        ),
        pytest.param(
            "assert",
            {"from": 0, "to": 1, "total_deposit": 100},
            None,
            None,
            "GET",
            f"http://0/api/v1/channels/{TEST_TOKEN_ADDRESS}/{NODE_ADDRESS_1}",
            {},
            200,
            {"total_deposit": "100"},
            id="assert-total_deposit",
        ),
        pytest.param(
            "assert",
            {"from": 0, "to": 1, "state": "open"},
            None,
            None,
            "GET",
            f"http://0/api/v1/channels/{TEST_TOKEN_ADDRESS}/{NODE_ADDRESS_1}",
            {},
            200,
            {"state": "open"},
            id="assert-state",
        ),
        pytest.param(
            "assert",
            {"from": 0, "to": 1, "balance": 100, "timeout": 0},
            ScenarioAssertionError,
            'Value mismatch for "balance". Should: "100" Is: "101"',
            "GET",
            f"http://0/api/v1/channels/{TEST_TOKEN_ADDRESS}/{NODE_ADDRESS_1}",
            {},
            200,
            {"balance": "101"},
            id="assert-balance-mismatch",
        ),
        pytest.param(
            "assert",
            {"from": 0, "to": 1, "balance": 100, "timeout": 0.1},
            ScenarioError,
            'Field "balance" is missing in channel',
            "GET",
            f"http://0/api/v1/channels/{TEST_TOKEN_ADDRESS}/{NODE_ADDRESS_1}",
            {},
            200,
            {},
            id="assert-balance-missing",
        ),
        pytest.param(
            "assert",
            {"from": 0, "to": 1, "balance": 100, "timeout": 2},
            None,
            None,
            "GET",
            f"http://0/api/v1/channels/{TEST_TOKEN_ADDRESS}/{NODE_ADDRESS_1}",
            {},
            [200, 200],
            [{"balance": "101"}, {"balance": "100"}],
            id="assert-retry",
        ),
    ],
)
def test_channel_task2(
    mocked_responses,
    api_task_by_name,
    task_name,
    task_params,
    expected_exception,
    expected_exception_message,
    expected_req_method,
    expected_req_url,
    expected_req_body,
    resp_code,
    resp_json,
):
    # See ``generic_task_test`` for an explanation of the parameters
    assert_task_test(
        mocked_responses=mocked_responses,
        api_task_by_name=api_task_by_name,
        task_name=task_name,
        task_params=task_params,
        expected_exception=expected_exception,
        expected_exception_message=expected_exception_message,
        expected_req_method=expected_req_method,
        expected_req_url=expected_req_url,
        expected_req_body=expected_req_body,
        resp_code=resp_code,
        resp_json=resp_json,
    )


def test_store_channel_info(mocked_responses, dummy_scenario_runner, api_task_by_name):
    """ Test store_channel_info task.

    Ensure the request return value is stored unmodified in the ScenarioRunner's ``task_storage``
    dictionary under the ``STORAGE_KEY_CHANNEL_INFO`` key.
    """

    mocked_responses.add(
        "GET",
        f"http://0/api/v1/channels/{TEST_TOKEN_ADDRESS}/{NODE_ADDRESS_1}",
        json={"something": 1},
        status=200,
    )
    task_instance = api_task_by_name("store_channel_info", {"from": 0, "to": 1, "key": "test"})

    task_instance()

    assert dummy_scenario_runner.task_storage[STORAGE_KEY_CHANNEL_INFO]["test"] == {"something": 1}


def test_store_channel_info_missing_key(api_task_by_name):
    """ Ensure store_channel_info detects a missing config parameter. """
    with pytest.raises(ScenarioError) as ex:
        api_task_by_name("store_channel_info", {"from": 0, "to": 1})
    assert 'Required config "key" not found' in str(ex)

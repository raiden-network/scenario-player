import pytest
from tests.unittests.constants import (
    NODE_ADDRESS_0,
    NODE_ADDRESS_1,
    NODE_ADDRESS_2,
    NODE_ADDRESS_3,
    TEST_TOKEN_NETWORK_ADDRESS,
)
from tests.unittests.tasks.utils import generic_task_test

from scenario_player.exceptions import ScenarioAssertionError

HOPS_0_1_2 = [NODE_ADDRESS_0, NODE_ADDRESS_1, NODE_ADDRESS_2]
HOPS_0_1_3_2 = [NODE_ADDRESS_0, NODE_ADDRESS_1, NODE_ADDRESS_3, NODE_ADDRESS_2]
ROUTE_0_1_2 = {"path": HOPS_0_1_2, "estimated_fee": 0}
ROUTE_0_1_3_2 = {"path": HOPS_0_1_3_2, "estimated_fee": 0}


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
        # Test basic functionality of the assert_pfs_history task
        pytest.param(
            "assert_pfs_history",
            {"source": 0, "request_count": 1, "routes_count": 1},
            None,
            None,
            "GET",
            f"http://pfs/api/v1/_debug/routes/{TEST_TOKEN_NETWORK_ADDRESS}/{NODE_ADDRESS_0}",
            {},
            200,
            {
                "request_count": 1,
                "responses": [
                    {"source": NODE_ADDRESS_0, "target": NODE_ADDRESS_2, "routes": [ROUTE_0_1_2]}
                ],
            },
            id="assert_pfs_history-simple",
        ),
        # Test that mismatching routes in assert_pfs_history produce the correct error message
        pytest.param(
            "assert_pfs_history",
            {"source": 0, "request_count": 1, "routes_count": 1, "expected_routes": [[0, 1, 2]]},
            ScenarioAssertionError,
            "Expected route [0, 1, 2] but got [0, 1, 3, 2] at index 0",
            "GET",
            f"http://pfs/api/v1/_debug/routes/{TEST_TOKEN_NETWORK_ADDRESS}/{NODE_ADDRESS_0}",
            {},
            200,
            {
                "request_count": 1,
                "responses": [
                    {"source": NODE_ADDRESS_0, "target": NODE_ADDRESS_2, "routes": [ROUTE_0_1_3_2]}
                ],
            },
            id="assert_pfs_history-expected-route-error-msg",
        ),
    ],
)
def test_service_task(
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

import json

import pytest


def generic_task_test(
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
    """ Execute given task class with given parameters.

    If ``expected_req_method`` is None the test assumes the task will not perform a request (e.g.
    because it raises an exception before getting to the request).

    If ``expected_exception`` (and optional ``expected_exception_message``) is given we assert
    this exception is actually raised.

    Combinations of both of the above behaviours allow to assert on these three cases:
      - Successful task execution
      - Exception raised before a request is performed (e.g. violated precondition)
      - Exception raised after a request is performed (e.g. processing return value)
    """
    task_instance = api_task_by_name(task_name, task_params)

    # If no expected method is passed we don't register an expected response
    # Useful if an exception will be raised before the request is performed
    if expected_req_method:
        mocked_responses.add(
            expected_req_method, expected_req_url, json=resp_json, status=resp_code
        )

    if expected_exception is not None:
        with pytest.raises(expected_exception) as ex:
            task_instance()
        if expected_exception_message:
            assert expected_exception_message in str(ex)
    else:
        response = task_instance()
        assert response == resp_json

    if expected_req_method:
        assert mocked_responses.calls[0].request.method == expected_req_method
        assert mocked_responses.calls[0].request.url == expected_req_url
        assert mocked_responses.calls[0].request.body.decode() == json.dumps(expected_req_body)
        assert mocked_responses.calls[0].response.json() == resp_json

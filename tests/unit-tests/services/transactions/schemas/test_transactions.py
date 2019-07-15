import pytest

from werkzeug.exceptions import BadRequest

from scenario_player.services.transactions.blueprints.transactions import TransactionSendRequest


@pytest.fixture
def default_request_parameters():
    """Default required request parameters for a POST request to /transactions.

    FIXME: Update the parameters once #96 is implemented.
     See here for more details:
        https://github.com/raiden-network/scenario-player/issues/96

    """
    parameters = {
        "chain_url": "http://test.net",
        "privkey": "1234abcd",
        "gas_price_strategy": "fast",
        "to": 'someaddress',
        "value": 123.0,
        "startgas": 2.0,
    }
    return parameters


@pytest.fixture
def deserialized_request_parameters(default_request_parameters):
    deserialized = dict(default_request_parameters)
    deserialized["to"] = deserialized["to"].encode("UTF-8")
    deserialized["privkey"] = deserialized["privkey"].encode("UTF-8")
    return deserialized


class TestTransactionSendRequestValidator:

    def test_validator_accepts_correct_input(self, default_request_parameters, deserialized_request_parameters):
        validator = TransactionSendRequest()
        assert validator.validate_and_deserialize(default_request_parameters) == deserialized_request_parameters

    def test_validator_raises_validation_error_on_missing_args(self):
        validator = TransactionSendRequest()
        parameters = {'to': 'some_hash', 'value': 123}
        with pytest.raises(BadRequest):
            validator.validate_and_deserialize(parameters)

    def test_validator_raises_validation_error_on_invalid_arg_type(self, default_request_parameters):
        validator = TransactionSendRequest()
        default_request_parameters["url"] = 55
        with pytest.raises(BadRequest):
            validator.validate_and_deserialize(default_request_parameters)

    def test_serializer_constructs_correct_output(self):
        serializer = TransactionSendRequest()
        tx_hash = b'my_tx_hash'
        given = {'tx_hash': tx_hash}
        expected_output = {'tx_hash': tx_hash.decode('utf-8')}
        actual = serializer.dump(given)
        assert actual == expected_output

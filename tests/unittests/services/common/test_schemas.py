import base64

import pytest
from eth_utils import decode_hex, encode_hex
from werkzeug.exceptions import BadRequest

from scenario_player.services.common.schemas import BytesField, SPSchema


@pytest.fixture
def random_bytes():
    with open("/dev/urandom", "rb") as f:
        return f.read(8)


@pytest.fixture
def test_schema():
    """Minimal schema to test the :class:`SPSchema` and :class:`BytesField` classes.

    Defines a single :class:`BytesField` at :attr:`.TestSchema.bytes_field` on the
    sub-class of :class:`SPSchema`.

    The sub-class is called :class:`TestSchema`.

    An instance of this sub-class is returned.
    """

    class TestSchema(SPSchema):
        bytes_field = BytesField(required=True)

    return TestSchema()


def test_bytesfield_deserializes_to_bytes_hex_decode(test_schema, random_bytes):
    """BytesField deserialized base64 encoded bytes to a string.

    The input string must have been encoded with :func:`base64.encodebytes` and
    subsequently enocded using `bytes.encode('ascii')`.
    """
    bytes_field = BytesField()
    input_string = encode_hex(random_bytes)
    expected = random_bytes

    assert bytes_field._deserialize(input_string, "bytes_field", {}) == expected


def test_bytesfield_serializes_to_string_using_hex_encode(test_schema, random_bytes):
    bytes_field = BytesField()
    # Represent bytes resulting in a view which needs to be serialized and sent in a JSON payload.
    input_string = random_bytes
    expected = encode_hex(input_string)

    assert bytes_field._serialize(input_string, "bytes_field", object()) == expected


@pytest.mark.parametrize(
    "input_dict, failure_expected",
    argvalues=[
        ({"bytes_field": encode_hex(b"my_string1")}, False),
        ({"bytes_field": "my_string"}, True),
        ({"bytes_field": b"my_string"}, True),
        ({"bytes_field": b""}, True),
        ({"bytes_field": ""}, True),
    ],
    ids=[
        "Hex string passes",
        "Non-Hexed string fails",
        "Invalid Non-empty Bytes fails",
        "Invalid Empty Bytes fails",
        "Invalid Empty String fails",
    ],
)
def test_spschema_validate_and_deserialize_raises_bad_request_when_expected(
    input_dict, failure_expected, test_schema
):
    try:
        test_schema.validate_and_deserialize(input_dict)
    except BadRequest:
        if failure_expected:
            return
        raise AssertionError(f"RAISED {BadRequest} unexpectedly!")

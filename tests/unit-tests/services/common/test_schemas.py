import pytest

from scenario_player.services.common.schemas import BytesField, SPSchema
from werkzeug.exceptions import BadRequest


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


def test_bytesfield_deserializes_to_utf_8_decoded_bytes(test_schema):
    """:meth:`Bytestfield._serialize` is expected to return a :class:`bytes` object,
    using UTF8 encoding.
    """
    bytes_field = BytesField()
    expected = b"my_string"
    input_string = expected.decode('UTF-8')

    assert bytes_field._deserialize(input_string, "bytes_field", {}) == expected


def test_bytesfield_serializes_to_utf_8_encoded_string(test_schema):
    """:meth:`Bytestfield._serialize` is expected to return a :class:`str` object
    using UTF-8 encoding.
    """
    bytes_field = BytesField()
    expected = "my_string"
    input_string = expected.encode('UTF-8')

    assert bytes_field._serialize(input_string, "bytes_field", object()) == expected


@pytest.mark.parametrize(
    "input_dict, failure_expected",
    argvalues=[
        ({'bytes_field': "my_string"}, False),
        ({'bytes_field': b"my_string"}, True),
        ({'bytes_field': b""}, True),
        ({'bytes_field': ""}, True),
    ],
    ids=[
        "Valid UTF8 string passes",
        "Invalid Non-empty Bytes fails",
        "Invalid Empty Bytes fails",
        "Invalid Empty String fails",
    ]
)
def test_spschema_validate_and_serialize_raises_bad_request_when_expected(input_dict, failure_expected, test_schema):
    try:
        test_schema.validate_and_deserialize(input_dict)
    except BadRequest:
        if failure_expected:
            return
        raise AssertionError(f"RAISED {BadRequest} unexpectedly!")

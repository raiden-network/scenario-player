import base64

import flask
from eth_utils import decode_hex, encode_hex
from flask_marshmallow.schema import Schema
from marshmallow.fields import String

try:
    from marshmallow import MarshalResult, UnmarshalResult
except ImportError:
    MarshalResult = UnmarshalResult = None


class SPSchema(Schema):
    """A modified :class:`.Schema` class, disallowing dumping of data using one of its instances.

    Provides a convenience method for validation and deserialization.
    """

    def validate_and_deserialize(self, data_obj) -> dict:
        """Validate `data_obj` and deserialize its fields to native python objects.

        If validation fails, this raises a :exc:`werkzeug.exceptions.BadRequest`,
        ending the request sequence.

        :raises werkzeug.exceptions.BadRequest:
            if validaing the `data_obj` did not succeed..
        """
        errors = self.validate(data_obj)
        if errors:
            flask.abort(400, str(errors))
        return self.load(data_obj)


class BytesField(String):
    """A field for (de)serializing :class:`bytes` from and to :class:`str` dict values."""

    default_error_messages = {
        "not_hex": "Must be a hex encoded string!",
        "not_bytes": "Must be decodable to bytes!",
        "empty": "Must not be empty!",
    }

    def __init__(self, *args, **kwargs):
        super(BytesField, self).__init__(*args, **kwargs)

    def _deserialize(self, value: str, attr, data, **kwargs) -> bytes:
        """Load the :class:`str` object for usage with the JSONRPCClient.

        `value` is expected to a bytes object encdoded to a string using
         :func:`base64.encodebytes`.

        This encodes the :class:`str` using 'ascii' and returns a :class:`bytes` object.

        If `kwargs` is not empty, we will emit a warning, since we do not currently
        support additional kwargs passed to this method.

        TODO: Implement support for additional `kwargs`
        """
        if not value:
            self.fail("empty")

        deserialized_string = super(BytesField, self)._deserialize(value, attr, data, **kwargs)

        try:
            return decode_hex(deserialized_string)
        except base64.binascii.Error:
            self.fail("not_hex")

    def _serialize(self, value: bytes, attr, obj, **kwargs) -> str:
        """Prepare :class:`bytes` object for JSON-encoding.

        This decodes the :class:`bytes` object using :func:`eth_utils.encode_hex`.
        """
        return super(BytesField, self)._serialize(encode_hex(value), attr, obj, **kwargs)

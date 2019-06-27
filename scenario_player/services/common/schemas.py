import flask
from flask_marshmallow.schema import Schema
from marshmallow.exceptions import ValidationError
from marshmallow.fields import Field


class SPSchema(Schema):
    """A modified :class:`.Schema` class, disallowing dumping of data using one of its instances.

    Provides a convenience method for validation and deserialization.
    """

    def validate_and_deserialize(self, data_obj):
        """Validate `data_obj` and deserialize its fields to native python objects.

        If validation fails, this raises a :exc:`werkzeug.exceptions.BadRequest`,
        ending the request sequence.
        """
        errors = self.validate(data_obj)
        if errors:
            flask.abort(400, str(errors))
        return self.load(data_obj).data


class BytesField(Field):
    """A field for (de)serializing :class:`bytes` from and to :class:`str` dict values."""

    def __init__(self, *args, **kwargs):
        super(BytesField, self).__init__(*args, **kwargs)
        self.validators.append(self._validate_encoding)
        self.validators.append(self._validate_length)

    @staticmethod
    def _validate_encoding(value: str):
        """Validate the field value is a UTF-8 decodable string object."""
        try:
            value.encode("UTF-8")
        except (AttributeError, UnicodeEncodeError):
            raise ValidationError("Bytesfield must be a UTF-8 encoded string!")
        return True

    @staticmethod
    def _validate_length(value: str):
        """Validate the field value is a non-empty string object."""
        if not len(value):
            raise ValidationError("Bytesfield must not be empty!")
        return True

    def _deserialize(self, value: str, attr, data):
        """Load the :class:`str` object for usage with the JSONRPCClient.

        This encodes the :class:`str` using UTF-8.
        """
        self._validate_encoding(value)
        self._validate_length(value)
        return value.encode("utf-8")

    def _serialize(self, value: bytes, attr, obj):
        """Prepare :class:`bytes` object for JSON-encoding.

        This decodes the :class:`bytes` object using UTF-8.
        """
        return value.decode("utf-8")

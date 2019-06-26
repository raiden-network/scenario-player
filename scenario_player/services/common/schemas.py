import flask

from marshmallow.exceptions import ValidationError
from marshmallow.fields import  Field
from marshmallow.schema import Schema


class ValidatorSchema(Schema):
    """A modified :class:`marshmallow.Schema` class, disallowing dumping of data using one of its instances.

    Provides a convenience method for validation and deserialization.
    """

    def validate_and_deserialize(self, data_obj):
        """Validate `data_obj` and deserialize its fields to native python objects.

        If validation fails, this calls `flask.abort(400, str(<dict of errors>)`,
        ending the request sequence.
        """
        try:
            return self.load(data_obj).data
        except ValidationError:
            flask.abort(400, str(errors))
        return self.load(data_obj)


class BytesField(Field):
    def _validate(self, value):
        try:
            value.encode('UTF-8')
        except (UnicodeEncodeError, AttributeError):
            raise ValidationError('Invalid input type.')

    def _deserialize(self, value: str, attr, data):
        return value.encode('utf-8')

    def _serialize(self, value: bytes, attr, obj):
        return value.decode('utf-8')

import flask

from marshmallow.exceptions import ValidationError
from marshmallow.fields import  Field
from marshmallow.schema import Schema


class ValidatorSchema(Schema):
    """A modified :class:`marshmallow.Schema` class, disallowing dumping of data using one of its instances.

    Provides a convenience method for validation and deserialization.
    """

    def validate_and_serialize(self, data_obj):
        """Validate `data_obj` and deserialize its fields to native python objects.

        If validation fails, this calls `flask.abort(400, str(<dict of errors>)`,
        ending the request sequence.
        """
        errors = self.validate(data_obj)
        if errors:
            flask.abort(400, str(errors))
        return self.load(data_obj).data


class BytesField(Field):
    def _validate(self, value):
        if type(value) is not bytes:
            raise ValidationError('Invalid input type.')

        if value is None or value == b'':
            raise ValidationError('Invalid BytesField value!')

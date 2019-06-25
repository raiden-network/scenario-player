import flask

from marshmallow.exceptions import ValidationError
from marshmallow.fields import  Field
from marshmallow.schema import Schema


class ValidatorSchema(Schema):
    """A modified :class:`marshmallow.Schema` class, disallowing dumping of data using one of its instances.

    Provides a convenience method for validation and deserialization.
    """

    def dump(self, *args, **kwargs):
        raise SyntaxError(f"ValidatorSchema subclasses cannot be used to dump data! {self.__class__.__qualname__}")

    def dumps(self, *args, **kwargs):
        raise SyntaxError(f"ValidatorSchema subclasses cannot be used to dump data! {self.__class__.__qualname__}")

    def validate_and_serialize(self, data_obj):
        """Validate `data_obj` and deserialize its fields to native python objects.

        If validation fails, this calls `flask.abort(400, str(<dict of errors>)`,
        ending the request sequence.
        """
        errors = self.validate(data_obj)
        if errors:
            flask.abort(400, str(errors))
        return self.load(data_obj)


class SerializerSchema(Schema):
    """A modified :class:`marshmallow.Schema` class, disallowing loading of data using one of its instances."""
    def load(self, *args, **kwargs):
        raise SyntaxError(f"SerializerSchema subclasses cannot be used to load data! {self.__class__.__qualname__}")

    def loads(self, *args, **kwargs):
        raise SyntaxError(f"SerializerSchema subclasses cannot be used to load data! {self.__class__.__qualname__}")


class BytesField(Field):
    def _validate(self, value):
        if type(value) is not bytes:
            raise ValidationError('Invalid input type.')

        if value is None or value == b'':
            raise ValidationError('Invalid BytesField value!')

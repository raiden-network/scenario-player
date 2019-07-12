import warnings

import flask
from flask_marshmallow.schema import Schema
from marshmallow.fields import Field
from marshmallow import UnmarshalResult, MarshalResult


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

    def load(self, data, data_only=True, **kwargs):
        # FIXME: This is a compatibility hack for new versions of marshmallow and
        #  our currently pinned 2.x verison. It automatically returns the data
        #  attribute by default, if load returns an UnmarshalResult object.
        result = super(SPSchema, self).load(data, **kwargs)

        if not isinstance(result, UnmarshalResult):
            # marshmallow-3.x no longer returns namedtuples, so we can safely
            # return the loaded object.
            return result
        elif data_only:
            # Return the data attribute only.
            return result.data
        return result

    def dumps(self, data, data_only=True, **kwargs):
        # FIXME: This is a compatibility hack for new versions of marshmallow and
        #  our currently pinned 2.x verison. It automatically returns the data
        #  attribute by default, if load returns an UnmarshalResult object.
        result = super(SPSchema, self).dumps(data, **kwargs)

        if not isinstance(result, MarshalResult):
            # marshmallow-3.x no longer returns namedtuples, so we can safely
            # return the dumped object.
            return result
        elif data_only:
            # Return the data attribute only.
            return result.data
        return result


class BytesField(Field):
    """A field for (de)serializing :class:`bytes` from and to :class:`str` dict values."""

    default_error_messages = {
        "not_a_str": "Must be string!",
        "not_bytes": "Must be decodable to bytes!",
        "empty": "Must not be empty!",
    }

    def __init__(self, *args, **kwargs):
        super(BytesField, self).__init__(*args, **kwargs)

    def _deserialize(self, value: str, attr, data, **kwargs) -> bytes:
        """Load the :class:`str` object for usage with the JSONRPCClient.

        This encodes the :class:`str` using UTF-8 and returns a :class:`bytes` object.

        If `kwargs` is not empty, we will emit a warning, since we do not currently
        support additional kwargs passed to this method.

        TODO: Implement support for additional `kwargs`
        """
        if kwargs:
            warnings.warn(
                f"Unsupported keywords for field {self.__class__.__qualname__} detected. "
                f"The following options will be ignored: {[option for option in kwargs]}"
            )

        if not value:
            self.fail("empty")

        try:
            return value.encode("UTF-8")
        except AttributeError:
            self.fail("not_a_str")

    def _serialize(self, value: bytes, attr, obj) -> str:
        """Prepare :class:`bytes` object for JSON-encoding.

        This decodes the :class:`bytes` object using UTF-8.
        """
        return value.decode("utf-8")

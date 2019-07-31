from marshmallow.fields import Field, Integer, Nested, Number, String, ValidationError

from scenario_player.services.common.schemas import BytesField, SPSchema
from scenario_player.services.rpc.schemas.base import RPCClientID, RPCCreateResourceSchema


class FunctionArgs(Nested):
    """Field for RPC Parameters.

    Load-only Field for deserializing RPC function parameters/arguments.
    """

    def __init__(self, *args, **kwargs):
        kwargs["load_only"] = True
        super(FunctionArgs, self).__init__(*args, **kwargs)

    def _deserialize(self, value: list, attr, data, **kwargs):
        if len(value) != len(self.nested):
            raise ValidationError(f"Field must be list of len {len(self.nested)}")

        deserialized = []
        for arg, validator in zip(value, self.nested):
            try:
                deserialized.append(validator._deserialize(arg, attr, data, **kwargs))
            except ValidationError as e:
                raise ValidationError(
                    f"Parameter {arg} could not be deserialized by {validator}!"
                ) from e
        return deserialized


class TokenCreateSchema(RPCCreateResourceSchema):
    """Validator for POST /rpc/token requests."""

    # Deserializer fields
    constructor_args = FunctionArgs(
        [Integer(required=True), String(required=True), String(required=True)], required=True
    )
    token_name = String(required=False, missing=None, load_only=True)

    # Serializer fields
    tx_hash = BytesField(required=True, dump_only=True)


class TokenMintSchema(RPCCreateResourceSchema):
    """Validator for POST /rpc/token/mint requests."""

    token_address = String(load_only=True, required=True)
    mint_target = String(load_only=True, required=True)
    amount = Number(load_only=True, required=True)

    # Serializer fields
    tx_hash = BytesField(required=True, dump_only=True)

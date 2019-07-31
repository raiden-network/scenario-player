from marshmallow.fields import Integer, Number, String, Tuple

from scenario_player.services.common.schemas import BytesField
from scenario_player.services.rpc.schemas.base import RPCCreateResourceSchema


class TokenCreateSchema(RPCCreateResourceSchema):
    """Validator for POST /rpc/token requests."""

    # Deserializer fields
    constructor_args = Tuple(
        [Integer(required=True), String(required=True), String(required=True)],
        required=True,
        load_only=True,
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

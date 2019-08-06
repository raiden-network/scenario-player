from flask_marshmallow import Schema
from marshmallow.fields import Integer, Nested, Number, String

from scenario_player.services.common.schemas import BytesField
from scenario_player.services.rpc.schemas.base import RPCCreateResourceSchema


class ConstructorArgsSchema(Schema):
    decimals = Integer(required=True)
    name = String(required=True)
    symbol = String(required=True)


class ContractSchema(Schema):
    """JSON object representing a deployed contract.

    Parameters:

        - name (string)
        - address (string)
    """

    #: name of the deployed contract.
    name = String(required=True)
    #: check-summed address of the deployed contract.
    address = String(required=True)


class TokenCreateSchema(RPCCreateResourceSchema):
    """Validator for POST /rpc/token requests.

    Load-only parameters:

        - constructor_args (:class:`ConstructorArgsSchema`)
        - token_name (string, optional)

    Dump-only parameters:

        - contract (:class:`ContractSchema`)
        - deployment_block (integer)
    """

    # Deserializer fields
    constructor_args = Nested(ConstructorArgsSchema, required=True, load_only=True)
    token_name = String(required=False, missing=None, load_only=True)

    # Serializer fields
    contract = Nested(ContractSchema, required=True, dump_only=True)
    deployment_block = Integer(required=True, dump_only=True)


class TokenMintSchema(RPCCreateResourceSchema):
    """Validator for POST /rpc/token/mint requests.

    Load-only parameters:

        - target_address (string)
        - contract_address (string)
        - amount (number)
        - gas_limit (number)

    Dump-only parameters:

        - tx_hash (:class:`BytesField`)
    """

    # Deserializer fields
    target_address = String(load_only=True, required=True)
    contract_address = String(load_only=True, required=True)
    amount = Number(load_only=True, required=True)
    gas_limit = Number(load_only=True, required=True)

    # Serializer fields
    tx_hash = BytesField(required=True, dump_only=True)

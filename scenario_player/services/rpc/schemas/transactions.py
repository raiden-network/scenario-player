from marshmallow.fields import Integer

from scenario_player.services.common.schemas import BytesField
from scenario_player.services.rpc.schemas.base import RPCCreateResourceSchema


class SendTransactionSchema(RPCCreateResourceSchema):
    """Validator for POST /rpc/transactions requests"""

    # Serialization fields.
    to = BytesField(required=True, load_only=True)
    startgas = Integer(required=True, load_only=True)
    value = Integer(required=True, load_only=True, as_string=False)

    # Deserialization fields.
    tx_hash = BytesField(required=True, dump_only=True)

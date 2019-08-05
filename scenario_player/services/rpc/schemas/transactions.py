from marshmallow.fields import Float

from scenario_player.services.common.schemas import BytesField
from scenario_player.services.rpc.schemas.base import RPCCreateResourceSchema


class TransactionSendRequest(RPCCreateResourceSchema):
    """Validator for POST /rpc/<rpc_client_id>/transactions requests"""

    # Serialization fields.
    to = BytesField(required=True, load_only=True)
    startgas = Float(required=True, load_only=True)
    value = Float(required=True, load_only=True, as_string=False)

    # Deserialization fields.
    tx_hash = BytesField(required=True, dump_only=True)

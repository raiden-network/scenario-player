from marshmallow.fields import String, Url

from scenario_player.services.common.schemas import BytesField, SPSchema
from scenario_player.services.rpc.schemas.base import RPCClientID, RPCCreateResourceSchema


class NewInstanceRequest(SPSchema):
    """POST /rpc/client

    load-only parameters:

        - chain_url (:class:`Url`)
        - privkey (:class:`BytesField`)
        - gas_price (str)

    dump-only parameters:

        - client_id (:class:`RPCClientID`)
    """

    # Deserialization fields.
    chain_url = Url(required=True, load_only=True)
    privkey = BytesField(required=True, load_only=True)
    gas_price_strategy = String(required=False, load_only=True, missing="fast")

    # Serialization fields.
    client_id = RPCClientID(required=True, dump_only=True)


class DeleteInstanceRequest(RPCCreateResourceSchema):
    """DELETE /rpc/client

    load-only parameters:

        - client_id (:class:`RPCClientID`)
    """

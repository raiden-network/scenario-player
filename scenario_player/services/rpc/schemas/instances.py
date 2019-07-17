from marshmallow.fields import Float, List, String, Url

from scenario_player.services.common.schemas import BytesField, SPSchema


class NewInstanceRequest(SPSchema):
    """Validator for POST /rpc/client requests."""
    # Deserialization fields.
    chain_url = Url(required=True, load_only=True)
    privkey = BytesField(required=True, load_only=True)
    gas_price_strategy = String(required=False, load_only=True, missing="fast")

    # Serialization fields.
    rpc_client_id = String(required=True, dump_only=True)


class DeleteInstanceRequest(SPSchema):
    """Validator for DELETE /rpc/client/<rpc_client_id> requests."""
    rpc_client_id = String(required=True)

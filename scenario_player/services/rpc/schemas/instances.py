from marshmallow.exceptions import ValidationError
from marshmallow.fields import String, Url

from scenario_player.constants import GAS_STRATEGIES
from scenario_player.services.common.schemas import BytesField, SPSchema
from scenario_player.services.rpc.schemas.base import RPCClientID, RPCCreateResourceSchema


class GasPrice(String):
    def _deserialize(self, value, attr, data, **kwargs):
        deserialzed = super(GasPrice, self)._deserialize(value, attr, data, **kwargs)
        try:
            return int(deserialzed)
        except ValueError:
            key = deserialzed.upper()
            if key in GAS_STRATEGIES:
                return key
            raise ValidationError(f"{value} - not an int-string or known gas price strategy!")


class CreateClientSchema(SPSchema):
    """POST /rpc/client

    load-only parameters:

        - chain_url (:class:`Url`)
        - privkey (:class:`BytesField`)
        - gas_price (str)

    dump-only parameters:

        - client_id (:class:`RPCClientID`)
    """

    # Deserialization fields.
    chain_url = Url(required=True, load_only=True, require_tld=False)
    privkey = BytesField(required=True, load_only=True)
    gas_price = GasPrice(required=False, load_only=True, missing="FAST")

    # Serialization fields.
    client_id = RPCClientID(required=True, dump_only=True)


class DeleteInstanceRequest(RPCCreateResourceSchema):
    """DELETE /rpc/client

    load-only parameters:

        - client_id (:class:`RPCClientID`)
    """

from marshmallow.fields import Float, List, String, Url

from scenario_player.services.common.schemas import BytesField, SPSchema


class TransactionSendRequest(SPSchema):
    """Validator for POST /transactions requests"""

    # FIXME: Remove these as soon as the Node Management Service is implemented.
    #  For more information, see the following issue:
    #       https://github.com/raiden-network/scenario-player/issues/96
    chain_url = Url(required=True)
    privkey = BytesField(required=True, load_only=True)
    gas_price_strategy = String(required=False, load_only=True, missing="fast")

    # Serialization fields.
    to = BytesField(required=True, load_only=True)
    startgas = Float(required=True, load_only=True)
    value = Float(required=True, load_only=True, as_string=False)

    # Deserialization fields.
    tx_hash = BytesField(required=True, dump_only=True)


class TransactionTrackRequest(SPSchema):
    """Validator for GET /transactions requests"""

    # Serialization fields.
    hashes = List(BytesField(), required=True, load_only=True)

    # Deserialization fields.
    missing = List(BytesField(), missing=[], dump_only=True)
    found = List(BytesField(), missing=[], dump_only=True)

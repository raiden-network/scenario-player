from marshmallow.fields import Float, List

from scenario_player.services.common.schemas import BytesField, SPSchema


class TransactionSendRequest(SPSchema):
    """Validator for POST /transaction requests"""

    # Serialization fields.
    to = BytesField(required=True, load_only=True)
    startgas = Float(required=True, load_only=True)
    value = Float(required=True, load_only=True)

    # Deserialization fields.
    tx_hash = BytesField(required=True, dump_only=True)


class TransactionTrackRequest(SPSchema):
    """Validator for GET /transaction requests"""

    # Serialization fields.
    hashes = List(BytesField(), required=True, load_only=True)

    # Deserialization fields.
    missing = List(BytesField(), missing=[], dump_only=True)
    found = List(BytesField(), missing=[], dump_only=True)

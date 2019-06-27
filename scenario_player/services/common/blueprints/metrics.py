from flask import Blueprint, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

metrics_blueprint = Blueprint("metrics_view", __name__)


@metrics_blueprint.route("/metrics", methods=["GET"])
def metrics_route():
    return Response(generate_latest, mimetype=CONTENT_TYPE_LATEST)

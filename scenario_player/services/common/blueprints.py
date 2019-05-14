from flask import Blueprint, Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST


metrics_view = Blueprint('metrics_view', __name__)


@metrics_view.route('/metrics', methods=['GET'])
def metrics_route():
    return Response(generate_latest, mimetype=CONTENT_TYPE_LATEST)
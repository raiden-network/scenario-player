from flask import Blueprint, Response, request
from werkzeug.exceptions import InternalServerError

admin_blueprint = Blueprint("admin_view", __name__)


def shutdown_server():
    """Shutdown the server using :func:`werkzeug.server.shutdown`."""
    func = request.environ.get("werkzeug.server.shutdown")
    if func is None:
        raise InternalServerError
    func()
    return Response(response="Server shutting down...", status=200)


@admin_blueprint.route("/shutdown", methods=["POST"])
def shutdown() -> Response:
    return shutdown_server()


@admin_blueprint.route("/status")
def status_view() -> Response:
    return Response(status=200)

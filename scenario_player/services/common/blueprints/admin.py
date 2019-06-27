from flask import Blueprint, request, Response


admin_blueprint = Blueprint("admin_view", __name__)


def shutdown_server():
    """Shutdown the server using :func:`werkzeug.server.shutdown`."""
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    func()


@admin_blueprint.route('/shutdown', methods=['POST'])
def shutdown():
    shutdown_server()
    return 'Server shutting down...'


@admin_blueprint.route("/status")
def status_view():
    return Response(status=200)
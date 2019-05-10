import flask

from scenario_player.services.releases.types import Dict, RaidenBinaryInfo, Union
from scenario_player.services.common.metrics import track_red_metrics



binaries_views = flask.Blueprint(__name__)


@app.route('/binaries', method=['GET', 'POST', 'DELETE'])
def binaries_route() -> Union[Dict[str, RaidenBinaryInfo], RaidenBinaryInfo]:
    handlers = {
        'POST': install_binary,
        'GET': list_local_binaries,
        'DELETE': uninstall_binary,
    }
    with track_red_metrics(request.method, '/binaries'):
        return handlers[request.method]()


def install_binary() -> RaidenBinaryInfo:
    """Installs a binary for the given `release`.

    If the release has not been downloaded and/or unpacked, this will be
    done automatically.

    ::

        POST /binaries

            {'version': <str>}

        200 OK

            {
                'version': <str>,
                'path': <str>,
                'archive_path': <str>,
            }
    """
    version = request.form['version']
    flask.abort(501)
    return {'version': version, 'path': '', 'archive': ''}


def list_local_binaries() -> Dict[str, RaidenBinaryInfo]:
    """Return the list of locally available binaries.

    ::

        GET /binaries

        200 OK

            {
                <version>: {'version': <str>, 'path': <str>, 'archive_path': <str>},
                ...
            }
    """
    flask.abort(501)


def uninstall_binary() -> None:
    """Uninstall the binary for the given release.

    This does not remove the cached binary, unless `purge=True` is given. Its
    default is `False`.

    ::

        DELETE /binaries?version=<str>&purge=<bool>

        204 No Content
    """
    version = request.args['version']

    def boolean_converter(value):
        if value.lower() in ('false', '0'):
            return False
        elif value.lower() in ('true', '1'):
            return True
        else:
            flask.abort(400, description="'purge' must be one of ('true', 'false', 0, 1)")

    purge = request.args.get('purge', default=False, type=boolean_converter)

    flask.abort(501)

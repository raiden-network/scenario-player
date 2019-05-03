import flask

from raiden.scenario_player.services.releases.types import Dict, RaidenArchiveInfo
from raiden.scenario_player.services.common.metrics import track_red_metrics

archives_views = flask.Blueprint(__name__)


@app.route('/archives', method=['GET', 'POST', 'DELETE'])
def archives_route() -> Dict[str, RaidenArchiveInfo]:
    handlers = {
        'POST': download_archive,
        'GET': downloaded_archives,
        'DELETE': delete_archive,
    }
    with track_red_metrics(request.method, '/archives'):
        return handlers[request.method]()


def download_archive() -> RaidenArchiveInfo:
    """Download the archive for the specified release.

    ::

        POST /archives

            {
                'version': <str>,
            }

        200 OK

            {
                'version': <str>,
                'path': <str>,
                'bin_path': None,
            }
    """
    version = request.form['version']
    return {'version': version, 'path': None, 'binary': None}


def downloaded_archives() -> Dict[str, RaidenArchiveInfo]:
    """Return a list of downloaded archives.

    ::

        GET /archives

        200 OK

            {
                <version>: {'version': <str>, 'path': <str>, 'bin_path': <str>},
                ...
            }
    """
    flask.abort(501)


def delete_archive() -> None:
    """Delete the cached binary file for the given release.

    ::

        DELETE /archives?version=<str>

        204 No Content
    """
    version = request.args['version']
    flask.abort(501)

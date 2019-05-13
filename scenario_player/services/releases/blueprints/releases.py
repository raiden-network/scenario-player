import flask

from scenario_player.services.releases.types import RaidenReleaseInfo, Dict
from scenario_player.services.common.metrics import track_red_metrics

releases_views = flask.Blueprint('releases_views', __name__)


# GET /releases
@releases_views.route('/releases', method=['GET'])
def return_available_releases() -> Dict[str, RaidenReleaseInfo]:
    """Return the list of raiden releases.

    ::

        GET /releases?only=<str>

        200 OK

            {
                <version>: {
                    'version': <str>,
                    'binary': <dict>,
                    'archive': <dict>
                },
                ...
            }

    """
    with track_red_metrics(request.method, '/releases'):
        filter = request.args.get('only', 'all')
        if filter and filter not in ('downloaded', 'installed', 'all'):
            flask.abort(404, description="'filter' must be one of 'downloaded', 'installed' or 'all'")

        flask.abort(501)
        return {'<version>': {'version': '', 'binary': {}, 'archive': {}}}


# GET /releases/latest
@releases_views.route('/releases/latest', method=['GET'])
def latest_release() -> RaidenReleaseInfo:
    """Return the latest release' version string.

    ::

        GET /releases/latest

        200 OK

            {
                'version': <str>,
                'binary': <dict>,
                'archive': <dict>
            }


    """
    with track_red_metrics(request.method, '/release/latest'):
        flask.abort(501)

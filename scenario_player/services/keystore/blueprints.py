import flask

from raiden.scenario_player.services.common.metrics import track_red_metrics

keystores_view = flask.Blueprint('keystores', __name__)


@keystores_view.route('/keystores', methods=['GET', 'POST', 'DELETE'])
def keystores_route():
    handlers = {
        'GET': list_keystores,
        'POST': create_keystore,
        'DELETE': remove_keystore,
    }
    with track_red_metrics(request.method, '/keystores'):
        return handlers[request.method]()


def list_keystores():
    """Return all available keystores registered with the server.

    ::

        GET /keystores

        200 OK

            {
                <keystore_id>: {
                    'keystore_id': <str>,
                    'path': <str>,
                    'name': <str>,
                    'comment': <str>,
                    'password': <str>,
                ),
                ...
            }
    """
    flask.abort(501)


def create_keystore():
    """Create a new keystore.

    ::

        POST /keystores

            {
                'name': <str>
                'comment':<str>
            }

        200 OK

            {
                'keystore_id': <str>,
                'path': <str>,
                'name': <str>,
                'comment': <str>,
                'password': <str>,
            }
    """
    fname = request.form['name']
    comment = request.form.get('comment', None)

    flask.abort(501)


def remove_keystore():
    """Remove the given keystore from the machine.

    ::

        DELETE /keystores?keystore_id=<str>

        204 NO CONTENT

        DELETE /keystores

        400 BAD Request

            "missing parameter: 'keystore_id'!"

    """
    keystore_id = request.args['keystore_id']
    flask.abort(501)

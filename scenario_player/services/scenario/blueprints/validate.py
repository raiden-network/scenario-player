import flask

from scenario_player.services.common.metrics import track_red_metrics

validate_view = flask.Blueprint('validate_view', __name__)


@validate_view.route('/scenarios/validate', methods=['POST'])
def scenarios_route():
    """Validate the submitted Scenario configuration.

    ::

        POST /scenarios/validate

            {
                scenario: <dict> | <file>
            }

        200 OK

        400 Bad Request

            {reason: "<description of faulty keys and values>"}
    """
    with track_red_metrics(request.method, '/scenarios/validate'):
        flask.abort(501)

import flask

from raiden.scenario_player.services.common.metrics import track_red_metrics

runner_view = flask.Blueprint(__name__)


@runner_view.route('/scenarios/run', methods=['POST', 'GET', 'DELETE'])
def scenario_run_route():
    """Execute and manage scenario runs on this machine."""
    handlers = {
        'POST': create_run,
        'GET': list_running,
        'DELETE': kill_run,
    }
    with track_red_metrics(request.method, '/scenarios/run'):
        return handlers[request.method]()


def create_run():
    """Create a new scenario run, executing a scenario specified by its `sid`.

    ::

        POST /scenarios/run

            {
                sid: <str>
            }

        200 OK

            {
                pid: <str>
            }

        404 Not Found

            {reason: 'Scenario with sid <sid> not found!'}


        POST /scenarios/run

        400 Bad Request

            {reason: "Missing parameter! 'sid'"}
    """
    flask.abort(501)


def list_running():
    """List the currently running scenarios by their `pid`.

    ::

        GET /scenarios/run

            {
                <pid>: {
                    sid: <str>,
                    started: <int>,
                },
                ...
            }
    """
    flask.abort(501)


def kill_run():
    """Kill a scenario run specified by its `pid`.

    ::

        DELETE /scenarios/run?sid=<str>

        204 No Content

        DELETE /scenarios/run

        400 Bad Request

            {reason: "Missing parameter! 'sid'"}
    """
    flask.abort(501)


@runner_view.route('/scenarios/run/state', methods=['GET'])
def scenario_state_route():
    """Return the state of the scenario run specified by its `pid`.

    ::

        GET /scenarios/run/state?pid=<str>

        200 OK

            {
                sid: <str>,
                pid: <str>,
                started: <int>,
                status: <str>,
                scenario: <dict>,
                stages: {
                    current: <str>,
                    time_spent_current: <float>,
                    time_spent_total: <float>,
                    remaining: <int>,
                    completed: <int>,
                }
                current_stage:{
                    name: <str>,
                    time_spent: <float>,
                }
                stages_remaining: <int>,
                stages_complete: <int>,
                errors: <list>,
            }

        400 Bad Request

            {reason: "Missing parameter! 'pid'"}

        404 Not Found

            {reason: 'Run with pid <pid> not found!'}

    """
    with track_red_metrics(request.method, '/scenarios/run/state'):
        flask.abort(501)

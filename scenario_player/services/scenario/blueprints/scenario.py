import flask

from scenario_player.services.common.metrics import track_red_metrics

scenario_view = flask.Blueprint(__name__)


@scenario_view.route('/scenarios', methods=['POST', 'GET', 'PUT', 'DELETE'])
def scenarios_route():
    handlers = {
        'POST': create_scenario,
        'GET': list_scenarios,
        'PUT': update_scenario,
        'DELETE': remove_scenario,
    }
    with track_red_metrics(request.method, '/scenarios'):
        return handlers[request.method]()


def create_scenario():
    """Create a new scenario.

    This allows creation of new scenario files programmatically via the API, or
    via file upload.

    ::

        POST /scenarios

            {
                name: <str>,
                description: <str>,
                scenario: <dict> | <file>,
                commit: <bool>,  # If False, the file is not checked into git.
            }

        200 OK

            {
                sid: <str>,
                name: <str>,
                description: <str>,
                scenario: <dict>,
                committed: <bool>,
            }

    """
    scenario_name = request.form['name']
    description = request.form['description']
    scenario = request.form['scenario']
    commit_to_vcs = request.form.get('commit', True)
    flask.abort(501)


def list_scenarios():
    """Return scenarios fitting the requested criteria.

    The scenarios can be filtered by scenario id (`sid`), `name`, or
    `scenario` settings.

    If the last option is used, the passed value **must**
    be a dict, and it must state full paths to the settings you'd like to filter
    after.

    If filtering by `name`, we use python's `in` operator to check if the passed
    string is present in the scenario's `name`, and add it to the returned
    response if that is the case.

    ::

        GET /scenarios

        200 OK

            {
                <sid>: {
                    sid: <str>,
                    name: <str>,
                    description: <str>,
                    scenario: <dict>,
                    committed: <bool>,
                },
                ...
            }

        200 OK

            {}

        GET /scenarios?name=<str>
        GET /scenarios?committed=<bool>
        GET /scenarios?scenario=<dict>

        200 OK

            {
                <sid>: {
                    sid: <str>,
                    name: <str>,
                    description: <str>,
                    scenario: <dict>,
                    committed: <bool>,
                },
                ...
            }

        404 Not Found

        GET /scenarios?sid=<str>

        200 OK

            {
                sid: <str>,
                name: <str>,
                description: <str>,
                scenario: <dict>,
                committed: <bool>,
            }

        404 Not Found

    """
    flask.abort(501)


def update_scenario():
    """Update an existing scenario.

    Calls `dict.update` on the scenario's root with the given `scenario` value.

    Also allows meta data to be updated such as `name`, `description` and the
    `committed` value.

    ::

        PUT /scenarios

            {
                <sid>:
                    {
                        name: <str>,
                        description: <str>,
                        scenario: <dict>,
                        commit: <bool>,
                    }
                ...,
                replace: <bool>,
            }

        200 OK

            {
                <sid>: {
                    sid: <str>,
                    name: <str>,
                    description: <str>,
                    scenario: <dict>,
                    committed: <bool>,
                },
                ...
            }
    """
    flask.abort(501)


def delete_scenario():
    """Delete the scenario specified by its `sid`.

    ::

        DELETE /scenarios?sid=<str>

        204 No Content
    """
    flask.abort(501)

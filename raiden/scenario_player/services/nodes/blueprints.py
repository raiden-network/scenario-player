from typing import Dict, Union

import flask

from raiden.scenario_player.services.common.metrics import track_red_metrics

nodes_view = flask.Blueprint(__name__)

NodeObj = Dict[str, Union[str, bool]]
NodeList = Dict[NodeObj]

#: Dict to keep track of registered Nodes. Should later be replaced by better solution (perhaps redis/memcached)
NODES = {}


@app.route('/nodes', methods=['POST', 'GET', 'DELETE'])
def node_route() -> Union[NodeObj, NodeList, None]:
    handlers = {
        "POST": create_node,
        "GET": list_nodes,
        "DELETE": destroy_node,
    }
    with track_red_metrics(request.method, '/nodes'):
        return handlers[request.method]()


def create_node() -> NodeObj:
    """Create a raiden node with the specified specs and configuration.

    ::

        POST /nodes

            {
                # Raiden version to use.
                'version': <str>,

                # The keystore file to use. Must be a keystore file ID.
                'keystore': <str>,

                # The chain to connect the binary instance to.
                'chain': <str>,

                # Whether or not to reclaim used ether.
                'reclaim-eth': <bool>,

                # Further CLI options to pass to the raiden binary
                'options': <dict>,

            }

        200 OK

            {
                # Node ID unique to this node instance.
                "node_id": <str>,

                'version': <str>,
                'keystore': <str>,
                'chain': <str>,
                'reclaim-eth': <bool>,
                'options': <dict>,
            }

    """
    version = request.data.get('version', 'latest')
    keystore = request.data['keystore']
    chain = request.data.get('chain', 'any')
    reclaim_eth = request.data.get('reclaim-eth', True)
    bin_options = request.data.get('options', {})

    flask.abort(501)


def list_all_nodes() -> NodeList:
    return NODES


def filter_by_state(nodes: NodeList, state: str) -> NodeList:
    if state not in ('running', 'stopped', 'killed', 'error'):
        raise ValueError(state)
    return {node_id: node_obj if node_obj['state'] == state for node_id, node_obj in nodes.items()}


def list_nodes() -> Union[NodeList, NodeObj]:
    """List all currently deployed Raiden nodes.

    Returned values may be filtered using the `state` parameter.
    Additionally, a `node_id` may be passed as well - in this case, only a dict
    matching this node_id is returned.

    If there are no objects matching the given parameters, a 404 Not Found
    is returned.

    ::

        GET /nodes

        200 OK

            {
                <node_id>: {
                    "node_id": <str>,
                    'version': <str>,
                    'keystore': <str>,
                    'chain': <str>,
                    'reclaim-eth': <bool>,
                    'options': <dict>,
                    "state": <str>,
                },
                ...
            }

        GET /nodes?node_id=<str>

        200 OK

            {
                "node_id": <str>,
                'version': <str>,
                'keystore': <str>,
                'chain': <str>,
                'reclaim-eth': <bool>,
                'options': <dict>,
                "state": <str>,
            }

        GET /nodes?state=<str>

        200 OK

            {
                <node_id>: {
                    "node_id": <str>,
                    'version': <str>,
                    'keystore': <str>,
                    'chain': <str>,
                    'reclaim-eth': <bool>,
                    'options': <dict>,
                    "state": <state>,
                },
                ...
            }

        GET /nodes?node_id=Non_Existing_Node_ID

        404 Not Found

    """
    try:
        filtered_nodes = filter_by_state(NODES, request.args['state'])
    except KeyError:
        filtered_nodes = None
    except ValueError:
        flask.abort(400, description=f"'state' must be one of 'running', 'stopped', 'killed' or 'error' - not '{state}'")

    nodes_subset = filtered_nodes or list_all_nodes()
    if 'node_id' in request.args:
        try:
            return nodes_subset[request.args['node_id']]
        except KeyError:
            flask.abort(404, description=f'Node with ID {request.args['node_id']} not found!')
    return nodes_subset


def destroy_node() -> Tuple[str, int]:
    """Destroy a node by the given node id.

    ::

        DELETE /nodes?node_id=<node_id>

        204 No Content

    """
    node_id = request.args['node_id']

    flask.abort(501)

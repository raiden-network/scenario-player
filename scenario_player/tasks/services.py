from __future__ import annotations

from typing import Any

import structlog

from scenario_player import runner as scenario_runner
from scenario_player.exceptions import ScenarioAssertionError, ScenarioError
from scenario_player.tasks.api_base import RESTAPIActionTask
from scenario_player.tasks.base import Task
from scenario_player.utils.datastructures import FrozenList

log = structlog.get_logger(__name__)


class AssertPFSRoutesTask(RESTAPIActionTask):
    """
    Assert PFS routes task

    Example usages:

        # Check that PFS response contains 2 routes
        assert_pfs_routes: {from: 0, to: 1, amount: 100, expected_paths: 2}

        # Check that PFS response contains 3 of 3 requested routes
        assert_pfs_routes: {source: 0, target: 1, amount: 100, max_paths: 3, expected_paths: 3}

        Default of `max_paths` is 5
    """

    _name = "assert_pfs_routes"
    _method = "post"
    _url_template = "{pfs_url}/api/v1/{token_network_address}/paths"

    @property
    def _request_params(self):
        source = self._config["from"]
        if isinstance(source, str) and len(source) == 42:
            source_address = source
        else:
            source_address = self._runner.get_node_address(source)

        target = self._config["to"]
        if isinstance(target, str) and len(target) == 42:
            target_address = target
        else:
            target_address = self._runner.get_node_address(target)

        amount = int(self._config["amount"])
        max_paths = int(self._config.get("max_paths", 5))

        params = {
            "from": source_address,
            "to": target_address,
            "value": amount,
            "max_paths": max_paths,
        }
        return params

    @property
    def _url_params(self):
        pfs_url = self._runner.yaml.settings.services.pfs.url
        if not pfs_url:
            raise ScenarioError("PFS tasks require settings.services.pfs.url to be set.")

        params = dict(pfs_url=pfs_url, token_network_address=self._runner.token_network_address)
        return params

    def _process_response(self, response_dict: dict):
        paths = response_dict.get("result")
        if paths is None:
            raise ScenarioAssertionError("No 'result' key in result from PFS")

        num_paths = len(paths)
        exptected_paths = int(self._config["expected_paths"])
        if num_paths != exptected_paths:
            log.debug("Received paths", paths=paths)
            raise ScenarioAssertionError(
                f"Expected {exptected_paths} paths, but PFS returned {num_paths} paths."
            )


class AssertPFSHistoryTask(RESTAPIActionTask):
    """
    Assert PFS history task

    Config options:

    Required:

      - ``source``:
        The node (address or index) of the source of the requested route(s).

    Optional:
      - ``target``:
        The node (address or index) of the target of the requested route(s).

      - ``request_count``
        The expected number of requests performed to the PFS with the given ``source``
        (and ``target`` if given).

      - ``routes_count``
        The expected number of routes returned.
        This can either be a list of counts for each expected responses or an integer in which case
        all responses must have the given route count.

      - ``expected_routes``
        Explicit list of expected routes.

      - ``distinct_routes_only``
        If set to true the list of routes is de-duplicated before being checked against
        ``expected_routes``.

    Example usages:

        # 4 requests where made from source node 0
        assert_pfs_history: {source: 0, request_count: 4}

        # 4 requests where made from source node 0 to target node 1
        assert_pfs_history: {source: 0, target: 1, request_count: 4}

        # 4 requests where made from source node 0 to target node 1 and 3 routes each have been
        # returned
        assert_pfs_history: {source: 0, target: 1, request_count: 4, routes_count: 3}

        # 4 requests where made from source node 0 to target node 1 and the specified number of
        # routes have been returned
        assert_pfs_history: {source: 0, target: 1, request_count: 4, routes_count: [3, 2, 1, 2]}

        # The listed routes have been returned for requests from source node 0 to target node 1
        assert_pfs_history:
          source: 0
          target: 1
          expected_routes:
            - ['0x00[...]01', '0x00[...]04']
            - ['0x00[...]01', '0x00[...]02', '0x00[...]04']

        # The listed *distinct* routes have been returned for requests from source node 0 to
        # target node 1.
        assert_pfs_history:
          source: 0
          target: 2
          distinct_routes_only: true
          expected_routes:
            - [0, 2]
            - [0, 1, 2]

    Expected response from PFS debug endpoint:
        {
            "request_count": <int>,
            "responses": [
                {
                    "source": <address>,
                    "target": <address>,
                    "routes": [
                    {
                        "path": [<address>, <address>, ...],
                        "estimated_fee": <estimated_fee>
                    }
                        ...,
                    ]
                },
                ...
            ]
        }
    """

    _name = "assert_pfs_history"
    _url_template = (
        "{pfs_url}/api/v1/_debug/routes/{token_network_address}/{source_address}{extra_params}"
    )

    @property
    def _url_params(self):
        pfs_url = self._runner.yaml.settings.services.pfs.url
        if not pfs_url:
            raise ScenarioError("PFS tasks require settings.services.pfs.url to be set.")

        source = self._config["source"]
        if isinstance(source, str) and len(source) == 42:
            source_address = source
        else:
            source_address = self._runner.get_node_address(source)

        extra_params = ""
        if "target" in self._config:
            target = self._config["target"]
            if isinstance(target, str) and len(target) == 42:
                target_address = target
            else:
                target_address = self._runner.get_node_address(target)
            extra_params = f"/{target_address}"

        params = dict(
            pfs_url=pfs_url,
            token_network_address=self._runner.token_network_address,
            source_address=source_address,
            extra_params=extra_params,
        )
        return params

    def _process_response(self, response_dict: dict):
        exp_request_count = self._config.get("request_count")
        if exp_request_count:
            actual_request_count = response_dict["request_count"]
            if actual_request_count != exp_request_count:
                raise ScenarioAssertionError(
                    f"Expected request_count {exp_request_count} but got {actual_request_count}"
                )

        actual_routes_counts = [len(response["routes"]) for response in response_dict["responses"]]
        exp_routes_counts = self._config.get("routes_count")
        if exp_routes_counts:
            if isinstance(exp_routes_counts, int):
                request_count = exp_request_count if exp_request_count else 1
                exp_routes_counts = [exp_routes_counts] * request_count
            elif isinstance(exp_routes_counts, (list, tuple)):
                if len(exp_routes_counts) != len(actual_routes_counts):
                    raise ScenarioAssertionError(
                        f"Expected {len(exp_routes_counts)} routes but got "
                        f"{len(actual_routes_counts)}"
                    )

            loop_iterator = enumerate(zip(exp_routes_counts, actual_routes_counts))
            for i, (exp_route_count, actual_route_count) in loop_iterator:
                if exp_route_count != actual_route_count:
                    raise ScenarioAssertionError(
                        f"Expected route count {exp_route_count} but got {actual_route_count} "
                        f"at index {i}"
                    )

        # We use a ``FrozenList`` because ``set`` (see below) doesn't accepts unhashable types
        actual_routes = FrozenList(
            FrozenList(route["path"])
            for response in response_dict["responses"]
            for route in response["routes"]
            if response["routes"]
        )

        if self._config.get("distinct_routes_only", False):
            # We only want distinct routes
            actual_routes = list(set(actual_routes))

        exp_routes = self._config.get("expected_routes")
        if exp_routes:
            if len(exp_routes) != len(actual_routes):
                raise ScenarioAssertionError(
                    f"Expected {len(exp_routes)} routes but got {len(actual_routes)}."
                )
            for i, (exp_route, actual_route) in enumerate(zip(exp_routes, actual_routes)):
                exp_route_addr = [self._runner.get_node_address(node) for node in exp_route]
                if exp_route_addr != actual_route:
                    raise ScenarioAssertionError(
                        f"Expected route {exp_route} but got {actual_route} at index {i}"
                    )

        exp_fees = self._config.get("expected_fees")
        if exp_fees:
            actual_fees = [
                route["estimated_fee"]
                for response in response_dict["responses"]
                for route in response["routes"]
                if response["routes"]
            ]
            if len(exp_fees) != len(actual_fees):
                raise ScenarioAssertionError(
                    f"Expected {len(exp_fees)} fees but got {len(actual_fees)}."
                )
            for i, (exp_fee, actual_fee) in enumerate(zip(exp_fees, actual_fees)):
                if exp_fee != actual_fee:
                    raise ScenarioAssertionError(
                        f"Expected fee {exp_fee} but got {actual_fee} at index {i}"
                    )


class AssertPFSIoUTask(RESTAPIActionTask):
    """
    Assert PFS IoU task

    Example usages:

        # IoUs of node 0 is stored at pfs with current amount 111
        assert_pfs_iou: {source: 0, amount: 111}

        # IoUs of node 0 is not stored in the pfs
        assert_pfs_iou: {source: 0, iou_exists: false}

    Expected response from PFS iou debug endpoint:
            {
                "sender": <address>,
                "amount": <int>,
                "exp_block": <int>,
            },

    """

    _name = "assert_pfs_iou"
    _url_template = "{pfs_url}/api/v1/_debug/ious/{source_address}"

    def __init__(
        self,
        runner: scenario_runner.ScenarioRunner,
        config: Any,
        parent: Task = None,
        abort_on_fail: bool = True,
    ) -> None:
        super().__init__(runner, config, parent, abort_on_fail)

        if "source" not in config:
            raise ScenarioError("Not all required keys provided. Required: source ")

        if not any(k in config for k in ["iou_exists", "amount"]):
            raise ScenarioError(f"Expected either iou_exists or amount.")

    @property
    def _url_params(self):
        pfs_url = self._runner.yaml.settings.services.pfs.url
        if not pfs_url:
            raise ScenarioError("PFS tasks require settings.services.pfs.url to be set.")

        source = self._config["source"]
        if isinstance(source, str) and len(source) == 42:
            source_address = source
        else:
            source_address = self._runner.get_node_address(source)

        params = dict(pfs_url=pfs_url, source_address=source_address)
        return params

    def _process_response(self, response_dict: dict):

        if self._config.get("iou_exists", True) is False:
            if response_dict:
                raise ScenarioAssertionError(f"Expected no IOU but got {response_dict}.")
        elif not response_dict:
            raise ScenarioAssertionError(f"Expected IOU, but no IOU exists.")
        else:
            exp_iou_amount = int(self._config["amount"])
            actual_iou_amount = int(response_dict["amount"])
            if actual_iou_amount != exp_iou_amount:
                raise ScenarioAssertionError(
                    f"Expected amount of {exp_iou_amount} but got {actual_iou_amount}."
                )

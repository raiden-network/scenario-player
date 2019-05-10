"""Fully modular service definitions for the Scenario Player stack.

Services can be run individually in a micro-service architecture, or as a
monolithic application.

The following services are defined:

    Node Service
        Creates and manages Raiden instances.

    Release Service
        Downloads, installs and manages Raiden releases, their archives and binaries.

    Keystore Service
        Creates and manages keystores required to run scenarios.

    Scenario Service
        Manages scenario files and offers an API for their creation, modification and execution.

Each service is instrumented using the :lib:`prometheus_client` library, and exposes a `/metrics`
endpoint when started, exposing `RED (Rate, Errors, Duration) metrics`_, in addition to service-specific metrics.

Exposed RED metrics names:

    http_exceptions_total
    http_requests_total
    http_requests_latency_seconds_sum
    http_requests_latency_seconds_count
    http_requests_latency_seconds_bucket[.005, .01, .025, .05, .075, .1, .25, .5, .75, 1.0, 2.5, 5.0, 7.5, 10.0, INF]

.. _RED (Rate, Errors, Duration) metrics: http://www.weave.works/blog/the-red-method-key-metrics-for-microservices-archiz2tecture/

"""
from scenario_player.services.keystore import create_keystore_service
from scenario_player.services.nodes import create_node_service
from scenario_player.services.releases import create_release_service
from scenario_player.services.scenario import create_scenario_service
from scenario_player.services.runner import create_runner_service
from scenario_player.services.server import create_master_service

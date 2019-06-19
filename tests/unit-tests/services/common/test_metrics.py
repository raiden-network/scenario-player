import time

import pytest

from prometheus_client import REGISTRY

from scenario_player.services.common.metrics import REDMetricsTracker


def trigger_metrics(method, path, wait=False, raise_exc=False):
    with REDMetricsTracker(method, path):
        print("printing stuff")
        if wait:
            print("waiting a few seconds..")
            time.sleep(2)
        if raise_exc:
            print("raising an exception..")
            raise ValueError
        print("Not raising an exception")
    print("Returning.")


class TestREDMetricContextManager:

    def test_requests_made_counter(self):
        method, path = 'TEST', 'PATH'
        before = REGISTRY.get_sample_value('http_requests_total', {'method': method, 'path': path}) or 0

        trigger_metrics(method, path)

        after = REGISTRY.get_sample_value('http_requests_total', {'method': method, 'path': path})
        assert after is not None
        assert after - before == 1

    def test_requests_exceptions_counter(self):
        method, path = 'TEST', 'PATH'
        before = REGISTRY.get_sample_value('http_exceptions_total', {'method': method, 'path': path}) or 0

        with pytest.raises(ValueError):
            trigger_metrics(method, path, raise_exc=True)

        after = REGISTRY.get_sample_value('http_exceptions_total', {'method': method, 'path': path})
        assert after is not None
        assert after - before == 1

    def test_request_latency_count(self):
        method, path = 'TEST', 'PATH'

        before = REGISTRY.get_sample_value('http_requests_latency_seconds_count', {'method': method, 'path': path}) or 0

        trigger_metrics(method, path, wait=True)

        after = REGISTRY.get_sample_value('http_requests_latency_seconds_count', {'method': method, 'path': path})
        assert after is not None
        assert after - before == 1

    def test_request_latency_sum(self):
        method, path = 'TEST', 'PATH'

        before = REGISTRY.get_sample_value('http_requests_latency_seconds_sum', {'method': method, 'path': path}) or 0

        trigger_metrics(method, path, wait=True)

        after = REGISTRY.get_sample_value('http_requests_latency_seconds_sum', {'method': method, 'path': path})
        assert after is not None

        diff = after - before

        # Check the difference is roughly in the ballpark of what we expect.
        assert (diff >= 2) and (diff <= 3)

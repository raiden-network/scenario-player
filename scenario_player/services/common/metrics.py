"""Prometheus Metrics used to monitor our flask applications.

Available metrics are:

    http_requests_total
        The total number of requests made to the application.

    http_exceptions_total
        The total number of exceptions raised during processing or requests. Please
        note that *404 Not Found* errors caused by requesting incorrect URLs are **NOT**
        included in this metric, since they are raised during routing, before the
        execution of any of our endpoint functions.

        However, `404 Not Found` exceptions raised explicitly by our functions
        are monitored.

    http_requests_latency_seconds
        The number of seconds required to process requests to endpoints of the
        application.

`method` and `path` labels are available for all metrics, allowing more granular
filtering using PromQL.

"""
import timeit

from prometheus_client import Counter, Histogram

HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total", "Total amount of HTTP Requests made.", labelnames=["method", "path"]
)
HTTP_EXCEPTIONS_TOTAL = Counter(
    "http_exceptions_total", "Total amount of HTTP exceptions.", labelnames=["method", "path"]
)
HTTP_REQUESTS_LATENCY = Histogram(
    "http_requests_latency_seconds",
    "Duration of HTTP requests processing.",
    labelnames=["method", "path"],
)


class REDMetricsTracker:
    """Prometheus RED metrics tracker class."""

    def __init__(self, method, path):
        self.method, self.path = method, path
        self.timer = None

    def __enter__(self):
        HTTP_REQUESTS_TOTAL.labels(self.method, self.path).inc()
        self.start = timeit.default_timer()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_val:
            HTTP_EXCEPTIONS_TOTAL.labels(self.method, self.path).inc()

        duration = max(timeit.default_timer() - self.start, 0)
        HTTP_REQUESTS_LATENCY.labels(self.method, self.path).observe(duration)

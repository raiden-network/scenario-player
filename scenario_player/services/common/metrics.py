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
from prometheus_client import Counter, Gauge, Histogram, Info, Summary


HTTP_REQUESTS_TOTAL = Counter('http_requests_total', 'Total amount of HTTP Requests made.', labelnamess=['method', 'path'])
HTTP_EXCEPTIONS_TOTAL = Counter('http_exceptions_total', 'Total amount of HTTP exceptions.', labelnames=['method', 'path'])
HTTP_REQUESTS_LATENCY = Histogram('http_requests_latency_seconds', 'Duration of HTTP requests processing.', labelnames=['method', 'path'])


def track_red_metrics(method, path):
    """Track metrics for requests to service endpoints.

    Tracks all relevant metrics to monitor rate, errors and duration of requests
    to and in our services.
    """
    HTTP_REQUESTS_TOTAL.labels(method, path).inc()
    with HTTP_EXCEPTIONS_TOTAL.labels(method, path).count_exceptions(), HTTP_REQUESTS_LATENCY.labels(method, path).time():
        yield

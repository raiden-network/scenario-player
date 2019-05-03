from prometheus_client import Counter, Gauge, Histogram, Info, Summary

HTTP_REQUESTS_TOTAL = Counter('http_requests_total', 'Total amount of HTTP Requests made.', labelnamess=['method', 'path'])
HTTP_EXCEPTIONS_TOTAL = Counter('http_exceptions_total', 'Total amount of HTTP exceptions.', labelnames=['method', 'path'])
HTTP_REQUESTS_LATENCY = Histogram('http_requests_latency_seconds', 'Duration of HTTP requests processing.', labelnames=['method', 'path'])


def track_red_metrics(method, path):
    """Track metrics for requests to service endpoints.

    Tracks all relevant metrics to monitor rate, errors and duration of requests to and in our services.
    """
    HTTP_REQUESTS_TOTAL.labels(method, path).inc()
    with HTTP_EXCEPTIONS_TOTAL.labels(method, path).count_exceptions(), HTTP_REQUESTS_LATENCY.labels(method, path).time():
        yield

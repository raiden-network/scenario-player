import requests


class ServiceProcessException(RuntimeError):
    """There was a problem with a :class:`ServiceProcess` instance."""


class ServiceError(ConnectionError):
    """There was an error while sending a request to/receiving a response from a SPaaS service.

    When this is raised from a requests.RequestException which occurred, we'll try
    and access the `request` attribute of the exception and access the service name and url
    of that request object. These are injected by the SPaaSAdapter and
    allow us to automagically build a minimally meaningful error message.

    Typically, errors subclassing from this exception are raised on the
    communication layer level (such as in the SPaaSAdapter and ServiceInterface classes).

    Raising them in other parts of the code should not be necessary.
    """

    def __init__(self, reason=None):
        reason = reason or self.__cause__ or ""
        if self.__cause__ and isinstance(self.__cause__, requests.HTTPError):
            request = self.__cause__.request

            try:
                service, service_path = request.service, request.orig_url
            except AttributeError:
                # Was not requested using the SPaaS adapter :< don't construct a message.
                pass
            else:
                message = f"Error communicating with '{service}' at '{service_path}'! {reason}"
                super(ServiceError, self).__init__(message)
        else:
            message = f"Error communicating with a desired service! {reason}"
            super(ServiceError, self).__init__(message)

    @property
    def response(self):
        if self.__cause__ and isinstance(self.__cause__, requests.HTTPError):
            return self.__cause__.response

    @property
    def request(self):
        if self.__cause__ and isinstance(self.__cause__, requests.HTTPError):
            return self.__cause__.request


class ServiceConnectionError(ServiceError):
    """An error occurred while trying to connect to a service endpoint.

    This exception is raised from:

        * :exc:`requests.ConnectionError`
        * :exc:`requests.Timeout`
    """


class ServiceUnreachable(ServiceConnectionError):
    """The url we specified could not be resolved.

    This may indicate that our targetservice is broken.

    Raised from:

        * :exc:`requests.ProxyError`
        * :exc:`requests.SSLError`
        * :exc:`requests.ConnectTimeout`
    """

    def __init__(self):
        reason = self.__cause__ or "Service Unreachable!"
        super(ServiceUnreachable, self).__init__(reason)


class ServiceReadTimeout(ServiceConnectionError):
    """The service was too slow when responding."""


class ServiceResponseError(ServiceError):
    """We received a response from the server, but there was a problem with it.

    Generally speaking, this is raised for any non-2xx-range http status codes.
    """


class BrokenService(ServiceError):
    """500 Internal Server Error was returned.

    This indicates a problem the with service we're trying to contact.
    """


class ServiceUnavailable(ServiceResponseError):
    """503 Service Unavailable was returned.

    This is typically due to an upstream service being broken, thus the service we're requesting
    cannot process our request at the moment.
    """

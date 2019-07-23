"""Programmatic interface for requesting SP services."""
from urllib.parse import urlparse, urlunparse

import requests
from requests.sessions import HTTPAdapter

from scenario_player.exceptions.services import (
    BrokenService,
    ServiceReadTimeout,
    ServiceUnavailable,
    ServiceUnreachable,
)
from scenario_player.utils.configuration.spaas import SPaaSConfig, SPaaSServiceConfig


class SPaaSAdapter(HTTPAdapter):
    """SPaaS Error handling for requests to its services.

    Handles requests made using the `spaas` scheme and maps the url to a configured
    service, if available. If no configuration for the service exists, we always
    assume it's available at localhost:5000 (the default flask port).
    """

    def __init__(self, spaas_settings: SPaaSConfig):
        super(SPaaSAdapter, self).__init__()
        self.config = spaas_settings

    def prep_service_request(self, request) -> requests.PreparedRequest:
        """Inject service's url into `request.url` and pass it to the parent method."""
        parsed = urlparse(request.url)
        # Add some meta data to the request object.
        request.orig_url = request.url
        request.service, *_ = parsed.netloc.split(":")

        # Load the service's configured url. Default to localhost if not present.
        service_conf = getattr(self.config, request.service, SPaaSServiceConfig({}))

        unparse_args = (
            service_conf.scheme or "https",
            service_conf.netloc or "localhost:5000",
            *parsed[2:],
        )
        request.url = urlunparse(unparse_args)

        return request

    @staticmethod
    def handle_connection_error(exc):
        """Raise ServiceConnectionError subclasses."""
        unreachable = (
            requests.exceptions.ProxyError,
            requests.exceptions.SSLError,
            requests.exceptions.ConnectTimeout,
        )
        if type(exc) == requests.exceptions.ReadTimeout:
            raise ServiceReadTimeout from exc
        elif type(exc) in unreachable:
            raise ServiceUnreachable from exc

    @staticmethod
    def handle_http_error(exc):
        """Raise ServiceResponseError subclasses.

        Evaluates exc.response.status_code to determine the exception to raise.

        If we do not find an exception for the status code of the response, we
        do not raise anything, allowing the response to be handed up to the
        requesting code instead.
        """
        if exc.response.status_code == 500:
            raise BrokenService from exc
        elif exc.response.status_code == 503:
            raise ServiceUnavailable from exc

    def send(self, request, stream=False, timeout=None, verify=True, cert=None, proxies=None):
        """Send the request to the service.

        This handles some of the error conversions of requests exceptions before
        other code gets the chance to do so. This makes business logic a little
        less cluttered, as it isn't required to wrap requests exceptions any longer.
        """
        request = self.prep_service_request(request)
        try:
            resp = super(SPaaSAdapter, self).send(request, stream, timeout, verify, cert, proxies)
        except (requests.Timeout, requests.ConnectionError) as e:
            self.handle_connection_error(e)
            raise
        try:
            resp.raise_for_status()
        except requests.HTTPError as e:
            self.handle_http_error(e)
        return resp


class ServiceInterface(requests.Session):
    def __init__(self, spaas_config: SPaaSConfig):
        super(ServiceInterface, self).__init__()
        self.config = spaas_config
        self.mount("spaas", SPaaSAdapter(self.config))

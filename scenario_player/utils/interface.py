"""Programmatic interface for requesting SP services."""
import subprocess
import uuid
from json import JSONDecodeError
from urllib.parse import urlparse, urlunparse

import requests
import structlog
from requests.sessions import HTTPAdapter
from simplejson import JSONDecodeError as SimpleJSONDecodeError

from scenario_player.exceptions.services import (
    BrokenService,
    ServiceReadTimeout,
    ServiceUnavailable,
    ServiceUnreachable,
)
from scenario_player.utils.configuration.spaas import SPaaSConfig, SPaaSServiceConfig

log = structlog.getLogger(__name__)


def spaas_services_up(service="stack") -> bool:
    """Check if the SPaaS Systemd Services are running.

    By default, checks if the 'stack' service, which includes all implemented services, is running.

    If you only installed a sub-set of the SPaaS services, you may check a single service by
    passing its name as the `service` parameter.

    This runs `systemd --user is-active` under the hood.
    """
    try:
        subprocess.run(
            f"systemctl --user is-active SPaaS-{service}.service".split(" "), check=True
        )
    except subprocess.CalledProcessError:
        return False
    return True


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
        path = f"{request.service}{parsed[2]}"
        unparse_args = (
            service_conf.scheme or "http",
            service_conf.netloc or "localhost:5000",
            path,
            *parsed[3:],
        )
        request.url = urlunparse(unparse_args)
        log.debug(event="service request", url=request.url, service=request.service)

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
            raise BrokenService(exc.response.text) from exc
        elif exc.response.status_code == 503:
            raise ServiceUnavailable(exc.response.text) from exc

    def send(self, request, stream=False, timeout=None, verify=True, cert=None, proxies=None):
        """Send the request to the service.

        This handles some of the error conversions of requests exceptions before
        other code gets the chance to do so. This makes business logic a little
        less cluttered, as it isn't required to wrap requests exceptions any longer.
        """
        request = self.prep_service_request(request)
        try:
            resp = super(SPaaSAdapter, self).send(request, stream, timeout, verify, cert, proxies)
        except (requests.Timeout, requests.ConnectionError, ConnectionError) as e:
            self.handle_connection_error(e)
            raise
        try:
            resp.raise_for_status()
        except requests.HTTPError as e:
            self.handle_http_error(e)

        try:
            resp.json()
        except (JSONDecodeError, SimpleJSONDecodeError) as e:
            log.debug(
                event="error while JSON-loading response",
                response=resp.text,
                request=request.url,
                exc=e,
            )
            raise

        return resp


class SPaaSPreparedRequest(requests.PreparedRequest):
    def __init__(self):
        super(SPaaSPreparedRequest, self).__init__()
        self.service = None
        self.orig_url = None


class ServiceInterface(requests.Session):
    def __init__(self, spaas_config: SPaaSConfig):
        super(ServiceInterface, self).__init__()
        self.config = spaas_config
        self.mount("spaas", SPaaSAdapter(self.config))

    def prepare_request(self, request):
        p = super(ServiceInterface, self).prepare_request(request)
        prepped = SPaaSPreparedRequest()
        prepped.method = p.method
        prepped.url = p.url
        prepped.body = p.body
        prepped._cookies = p._cookies
        prepped.headers = p.headers
        prepped.hooks = p.hooks
        prepped._body_position = p._body_position

        return prepped

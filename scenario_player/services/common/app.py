import multiprocessing as mp

import requests
import structlog
import waitress

from scenario_player.exceptions.services import ServiceProcessException
from scenario_player.services.utils.factories import construct_flask_app

log = structlog.getLogger(__name__)


class ServiceProcess(mp.Process):
    """:class:`multiprocessing.Process` subclass for running the SP services.

    The class's :meth:`.stop` method checks the server status and shuts it down
    via a POST request.

    Instances of this class have their :attr:`.daemon` attribute **always** set
    to `True`, regardless of any keywords passed to the class constructor.
    It can only be overridden by setting it after class initialization.

    Should the service not be reachable, it calls :meth:`.kill` instead, since
    the assumption is that it is stuck in a deadlock.

    Also offers a :func:`.app_is_responsive` property, which returns a boolean.
    This return `True` if a `GET /status` request returns a response (the status
    code does not matter) and `False` if a connection error or timeout occurred.
    """

    def __init__(self, *args, host: str = "127.0.0.1", port: int = 5000, **kwargs):
        if "target" in kwargs:
            raise ValueError("'target' is not supported by this class!")
        super(ServiceProcess, self).__init__(*args, **kwargs)
        self.daemon = True
        self.host = host
        self.port = port

    @property
    def is_reachable(self) -> bool:
        try:
            requests.get(f"http://{self.host}:{self.port}/status")
        except (requests.ConnectionError, requests.Timeout):
            # The service does not appear to be reachable.
            return False
        else:
            return True

    def stop(self) -> None:
        """Gracefully stop the service, if possible. Otherwise, kill it.

        This depends on if and how the Service's `/shutdown` endpoint responds.
        If we cannot connect to it, or our request times out, we assume the service
        is dead in the water and kill it.

        If we do get a response, but its status code is not in the `2xx` range,
        we check if the service is otherwise working, by making a GET request to
        the `/status` endpoint. If this does succeed, we must assume the
        shutdown sequence is faulty, and raise a :exc:`ServiceProcessException`.

        .. Note::

            In order for this method to work correctly, it requires the
            :var:`scenario_player.services.common.blueprints.admin_blueprint`
            to be registered with the app to gracefully shut it down.

            Should the blueprint not be registered, it will *always* call :meth:`.kill`.

        :raises ServiceProcessException: if we failed to shut down the service.
        """
        shutdown_type = "werkzeug.server.shutdown"
        try:
            resp = requests.post(f"http://{self.host}:{self.port}/shutdown")
        except (requests.ConnectionError, requests.Timeout):
            # The server is not responding. Kill it with a hammer.
            shutdown_type = "SIGKILL"
            return self.kill()
        else:
            try:
                resp.raise_for_status()
            except requests.HTTPError:
                if self.is_reachable:
                    # The server doesn't want to play ball - "gently" terminate its ass.
                    shutdown_type = "SIGTERM"
                    self.terminate()
        finally:
            if self.is_reachable:
                # The server still exists.Notify a human about its insubordinantion.
                raise ServiceProcessException("Shutdown sequence could not be initialized!")

            log.info("SPaaS Server shutdown", shutdown_type=shutdown_type)

    def run(self):
        """Run the Service."""
        app = construct_flask_app()
        waitress.serve(app, host=self.host, port=self.port)

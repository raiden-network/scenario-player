import argparse
import atexit
import os
import pathlib
import signal
import sys
from typing import Mapping

import flask

from scenario_player.hooks import SP_PM


def construct_flask_app(
    db_name: str = "default",
    test_config: Mapping = None,
    secret: str = "dev",
    config_file: str = "config.py",
    enable_plugins: bool = True,
) -> flask.Flask:
    """Construct a flask app with a set of default blueprints registered.

    By default all constructed apps use the :var:`admin_blueprint` and
    :var:`metrics_blueprint`, and therefore have the following endpoints:

        `/metrics`
        Exposes prometheus compatible metrics, if available.

        `/status`
        Returns 200 OK as long as the underlying flask app is responsive and running.

        `/shutdown`
        Shuts the server down gracefully.

    Additionally, any blueprints supplied by plugins are also automatically injected,
    unless `enable_plugins` is `False`.
    """
    # create and configure the app
    app = flask.Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(SECRET_KEY=secret, DATABASE=db_name)

    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_pyfile(config_file, silent=True)
    else:
        # load the test config if passed in
        app.config.from_mapping(test_config)

    if enable_plugins:
        # Register blueprints supplied by plugins.
        SP_PM.hook.register_blueprints(app=app)

    return app


def daemonize(pidfile: pathlib.Path, *, stdin="/dev/null", stdout="/dev/null", stderr="/dev/null"):
    """Daemonize the currently run script, using a double fork.

    Any commands executed after this function is called will be run in the daemonized process.

    Usage::

        if __name__ == "__main__":
            daemonize("/tmp/my_daemon.pid")
            my_func_to_run_daemonized()

    """
    if pidfile.exists():
        raise RuntimeError("Already running")

    # First fork (detaches from parent)
    try:
        if os.fork() > 0:
            raise SystemExit(0)  # Parent exit
    except OSError:
        raise RuntimeError("fork #1 failed.")

    os.chdir("/")
    os.umask(0)
    os.setsid()
    # Second fork (relinquish session leadership)
    try:
        if os.fork() > 0:
            raise SystemExit(0)
    except OSError:
        raise RuntimeError("fork #2 failed.")

    # Flush I/O buffers
    sys.stdout.flush()
    sys.stderr.flush()

    # Replace file descriptors for stdin, stdout, and stderr
    with open(stdin, "rb", 0) as f:
        os.dup2(f.fileno(), sys.stdin.fileno())
    with open(stdout, "ab", 0) as f:
        os.dup2(f.fileno(), sys.stdout.fileno())
    with open(stderr, "ab", 0) as f:
        os.dup2(f.fileno(), sys.stderr.fileno())

    # Write the PID file
    pidfile.write_text(str(os.getpid()))

    # Arrange to have the PID file removed on exit/signal
    atexit.register(lambda: pidfile.unlink())

    # Signal handler for termination (required)
    def sigterm_handler(signo, frame):
        raise SystemExit(1)

    signal.signal(signal.SIGTERM, sigterm_handler)


def start_daemon(pid_file: pathlib.Path, func, *args, stdout=None, stderr=None, **kwargs):
    """Run a function as a daemon process.

    Takes care of redirecting stdout and stderr to a logfile, instead of /dev/null.

    Any additional args and kwargs are passed to `func`.
    """
    stdout = stdout or "/var/log/scenario-player/{func.__name__}.stdout"
    stderr = stderr or "/var/log/scenario-player/{func.__name__}.stderr"
    try:
        daemonize(pid_file, stdout=stdout, stderr=stderr)
    except RuntimeError as e:
        print(e, file=sys.stderr)
        raise SystemExit(1)

    func(*args, **kwargs)


def stop_daemon(pid_file: pathlib.Path):
    """Stop the daemon with the given `pid_file`."""
    if pid_file.exists():
        pid = int(pid_file.read_text())
        os.kill(pid, signal.SIGTERM)
    else:
        print("Not running", file=sys.stderr)
        raise SystemExit(1)


def default_service_daemon_cli():
    """Create an :class:`argparse.ArgumentParser` with a minimalistic set of CLI options.

    Configures the following options:

        * <command> (required) - must be one of `start` or `stop`.
        * --port (optional) - the port to assign to the service. Defaults to 5000.
        * --host (optional) - the host to assign to the service. Defaults to 127.0.0.1
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["start", "stop"])
    parser.add_argument(
        "--port",
        default=5000,
        help="Port number to run this service on. Defaults to '5000'",
        type=int,
    )
    parser.add_argument(
        "--host", default="127.0.0.1", help="Host to run this service on. Defaults to '127.0.0.1'"
    )
    parser.add_argument("--log-service", default=None, help="netloc of a SPaaS Logging Service.")
    parser.add_argument(
        "--raiden-dir",
        default=pathlib.Path.home().joinpath(".raiden"),
        help="Path to the .raiden dir. defaults to ~/.raiden",
        type=pathlib.Path,
    )
    return parser

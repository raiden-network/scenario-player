"""Helper module for starting and stopping executables.

This uses the :mod:`mirakuru` library to start, stop and supervise a subprocess.

It allows us to check that the process is actually running, using the HTTP API exposed
by the :class:`mirakuru.HTTPExecutor`, and also that it does not terminate in an
unexpected fashion.
"""
import os
import platform
import subprocess
import typing

import mirakuru
import structlog

if typing.TYPE_CHECKING:
    from scenario_player.setup.nodes.flags import RaidenFlags

log = structlog.getLogger(__name__)


class ClientExecutor(mirakuru.HTTPExecutor):
    """Mirakuru Executor Subclass with a few customizations and forward-ports.

    Supports passing `timeout` parameter to the :meth:`.stop` method, a feature that
    was removed in mirakuru 1.1.0 and later.

    Allows redirecting stdout and stderr when calling :meth:`.start`, defaulting
    to :var:`subprocess.PIPE`, by passing the parameters `stdout` and `stderr`,
    respectively.

    Instances of this class have their default `timeout` parameter set to 300.
    """

    def __init__(self, *args, timeout: int = 300, **kwargs):
        super().__init__(*args, timeout=timeout, **kwargs)

    def start(self, stdout=subprocess.PIPE, stderr=subprocess.PIPE):
        """Custom :meth:`.mirakuru.HTTPExecutor.start` method allowing stderr/stdout redirects."""
        if self.pre_start_check():
            # Some other executor (or process) is running with same config:
            raise mirakuru.exceptions.AlreadyRunning(self)

        if self.process is None:
            command = self.command
            if not self._shell:
                command = self.command_parts

            env = os.environ.copy()
            env[mirakuru.base.ENV_UUID] = self._uuid
            popen_kwargs = {
                "shell": self._shell,
                "stdin": subprocess.PIPE,
                # Custom Code starts here
                "stdout": stdout,
                "stderr": stderr,
                # End of custom code
                "universal_newlines": True,
                "env": env,
            }
            if platform.system() != "Windows":
                popen_kwargs["preexec_fn"] = os.setsid
            self.process = subprocess.Popen(command, **popen_kwargs)

        self._set_timeout()

        self.wait_for(self.check_subprocess)
        return self

    def stop(self, sig=None, timeout=10):
        """Custom :meth:`.mirakuru.HTTPExecutor.stop` method allowing setting a timeout.

        The :attr:`._timeout` is temporarily changed, but restored after
        calling super().

        If an exception occurs during the super() call, the attribute is still
        restored.

        If the process is interrupted (i.e. SIGTERM'd or SIGKILL'd), the attribute
        will not be restored.
        """
        global_timeout = self._timeout
        self._timeout = timeout

        try:
            return super().stop(sig)
        finally:
            self._timeout = global_timeout


class RaidenExecutor(ClientExecutor):
    """Raiden Client Executor class.

    The command is constructed from the `raiden_flags` argument. In addition,
    it also exposes all of the flags' attributes, for convenient access.
    """
    def __init__(self, raiden_flags: "RaidenFlags", chain_id, data_path, log_file, *args, **kwargs):
        command = raiden_flags.as_cli_command(chain_id, data_path, log_file)
        super(RaidenExecutor, self).__init__(command, *args, **kwargs)
        self.flags = raiden_flags

    def __getattr__(self, item):
        try:
            return getattr(self, item)
        except AttributeError as e:
            try:
                return getattr(self.flags, item)
            except:
                raise e

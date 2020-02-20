import structlog

from scenario_player.tasks.base import Task

log = structlog.get_logger(__name__)


class ProcessTask(Task):
    _name = "process"
    _command = ""

    def _run(self, *args, **kwargs):
        method = getattr(self._runner.node_controller[self._config], self._command)
        method()

    def _handle_process(self, greenlet):  # pylint: disable=no-self-use
        greenlet.join()
        greenlet.get()


class StartNodeTask(ProcessTask):
    _name = "start_node"
    _command = "start"

    def _handle_process(self, greenlet):
        # FIXME: Wait for port to become available and then stop blocking on the greenlet
        super()._handle_process(greenlet)


class StopNodeTask(ProcessTask):
    _name = "stop_node"
    _command = "stop"


class KillNodeTask(ProcessTask):
    _name = "kill_node"
    _command = "kill"


class UpdateNodeOptionsTask(Task):
    _name = "update_node_options"

    def _run(self, *args, **kwargs):
        self._runner.node_controller[self._config["node"]].update_options(self._config["options"])

from typing import Any, List

import click
import gevent
import structlog
from gevent import Greenlet
from gevent.pool import Pool

from scenario_player import runner as scenario_runner
from scenario_player.tasks.base import Task, TaskState, get_task_class_for_type

log = structlog.get_logger(__name__)


class SerialTask(Task):
    _name = "serial"
    SYNCHRONIZATION_TIME_SECONDS = 0

    def __init__(
        self, runner: scenario_runner.ScenarioRunner, config: Any, parent: "Task" = None
    ) -> None:
        super().__init__(runner, config, parent)
        self._name = config.get("name")

        self._tasks: List = []
        for _ in range(config.get("repeat", 1)):
            for task in self._config.get("tasks", []):
                for task_type, task_config in task.items():
                    task_class = get_task_class_for_type(task_type)
                    self._tasks.append(
                        task_class(runner=self._runner, config=task_config, parent=self)
                    )

    def _run(self, *args, **kwargs):  # pylint: disable=unused-argument
        for task in self._tasks:
            task()

    @property
    def _str_details(self):
        name = ""
        if self._name:
            name = f' - {click.style(self._name, fg="blue")}'
        tasks = "\n".join(str(t) for t in self._tasks)
        return f"{name}\n{tasks}"

    @property
    def _urwid_details(self):
        if not self._name:
            return []
        return [" - ", ("task_name", self._name)]


class ParallelTask(SerialTask):
    SYNCHRONIZATION_TIME_SECONDS = 0
    _name = "parallel"

    def _run(self, *args, **kwargs):
        pool = Pool(size=self._config.get("concurrency", None))
        for task in self._tasks:
            pool.start(Greenlet(task))
        pool.join(raise_error=True)


class SnapshotTask(SerialTask):
    _name = "snapshot"

    def __init__(
        self, runner: scenario_runner.ScenarioRunner, config: Any, parent: "Task" = None
    ) -> None:
        super().__init__(runner, config, parent)

        self._runner.node_controller.snapshot_manager.check_scenario_config()
        if not self._runner.definition.nodes.restore_snapshot:
            log.warning("Snapshot task without 'nodes.restore_snapshot' configuration!")

        self._restored = self._runner.node_controller.snapshot_restored
        log.info("Snapshot task", was_restored=self._restored, config=self._config)

    def _run(self, *args, **kwargs):
        if not self._restored:
            super()._run(*args, **kwargs)
            self._runner.node_controller.stop()
            self._runner.node_controller.snapshot_manager.take()
            self._runner.node_controller.start()
        else:
            log.info("Skipping tasks, restored from snapshot")

    @property
    def _urwid_details(self):
        if self._restored:
            state = "Skipping, snapshot restored"
        else:
            if self.state is TaskState.INITIALIZED:
                state = "Will take snapshot"
            elif self.state is TaskState.RUNNING:
                state = "Taking snapshot"
            else:
                state = "Snapshot taken"
        return [" - ", ("task_name", state)]


class WaitTask(Task):
    _name = "wait"
    SYNCHRONIZATION_TIME_SECONDS = 0

    def _run(self, *args, **kwargs):  # pylint: disable=unused-argument
        gevent.sleep(self._config)


class WaitBlocksTask(Task):
    _name = "wait_blocks"
    SYNCHRONIZATION_TIME_SECONDS = 0

    def _run(self, *args, **kwargs):  # pylint: disable=unused-argument
        web3 = self._runner.client.web3
        start_block = web3.eth.blockNumber
        end_block = start_block + int(self._config)

        while web3.eth.blockNumber < end_block:
            gevent.sleep(10)


class WaitForInputTask(Task):
    """
    WARNING: This is a debugging feature. Things can break if
      - there are parallel tasks
      - you are using the UI
    """

    _name = "wait_input"
    SYNCHRONIZATION_TIME_SECONDS = 0

    def _run(self, *args, **kwargs):  # pylint: disable=unused-argument
        typed = ""
        while typed != "continue":
            typed = input("Waiting: Please type 'continue' to proceed!\n").strip()

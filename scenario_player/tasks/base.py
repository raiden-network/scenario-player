import importlib
import inspect
import pkgutil
import time
from copy import copy
from datetime import timedelta
from enum import Enum
from typing import Any, Dict, Optional, Type

import click
import gevent
import structlog
from gevent import Timeout, sleep

from scenario_player import runner as scenario_runner
from scenario_player.exceptions import ScenarioAssertionError, UnknownTaskTypeError

log = structlog.get_logger(__name__)

NAME_TO_TASK: Dict[str, Type["Task"]] = {}


class TaskState(Enum):
    INITIALIZED = " "
    RUNNING = "•"
    FINISHED = "✔"
    ERRORED = "✗"


TASK_STATE_COLOR = {
    TaskState.INITIALIZED: "",
    TaskState.RUNNING: click.style("", fg="yellow", reset=False),
    TaskState.FINISHED: click.style("", fg="green", reset=False),
    TaskState.ERRORED: click.style("", fg="red", reset=False),
}

_TASK_ID = 0


class Task:
    _name: str

    # The tasks in a scenario are written with the assumption of global
    # consistency, which is wrong. Consider the following scenario:
    #
    #    - open_channel: {from: 0, to: 1, total_deposit: 1_000}
    #    - open_channel: {from: 1, to: 2, total_deposit: 1_000}
    #    - transfer: {from: 0, to: 2, amount: 1}
    #
    # There are multiple system runnning concurrently that must be synchronized for
    # the `transfer` above to work:
    #
    # 1. The initiator (node 0) has to see the open event for the channel `1-2`.
    # This is necessary since the initiator will verify that at least one route to
    # the target exists, this is done to avoid sending unecessary IOUs to the PFS,
    # without the route the payment fails (In general the initiator has to see all
    # channel open events for every channel used in the path).
    # 2. The node receiving a lock must see the deposit of the sender. In the case
    # above node 1 has to see the deposit from node 0, and node 2 from node 1. If
    # this is not satisfied a locked transfer message will be rejected. Note:
    # Retries at the transport layer *do* fix this particular problem (In general,
    # every payee (mediator or target) have to see the deposit of the payer).
    # 3. The PFS used by the initiator (node 0), has to see the all channel opens
    # used by the transfer. This is necessary because the PFS has to find a viable
    # route in the network, and edges are added to the network graph based on these
    # events. (as of 0.9.0 deposits are not important).
    # 4. Every node in the path has to update the PFS with a capacity update. This
    # is necessary to determine the available off-chain balances (specially since
    # on-chain deposits are ignored by the PFS). And a fee update is necessary for
    # the sender.
    #
    # None of the above consistency checks are currently performed. Other
    # actions, like assert on the state of a channel after a close or settle,
    # checking monitoring requests, etc. also require additional
    # synchronization. Eventually the synchronization will have to be
    # implemented, since that is the only reliable way of preventing flakiness
    # of the scenarios. But until the proper synchronization is performed we
    # have to add enough time for every agent in the network to synchronize.
    # This is what the value below is used for, it determines the number of
    # seconds  available for the agents in the system to synchronize. The value
    # is applied after every task to cover for any unforseen side effects,
    # tasks that are side-effect free can overwrite the value to 0.
    #
    # Ref.: https://github.com/raiden-network/raiden/issues/6149#issuecomment-627387624
    SYNCHRONIZATION_TIME_SECONDS = 0  # keep the code for now, can be removed in the future
    DEFAULT_TIMEOUT = 0  # Tasks that need retries need to overwrite this

    def __init__(
        self, runner: scenario_runner.ScenarioRunner, config: Any, parent: "Task" = None
    ) -> None:
        global _TASK_ID

        _TASK_ID = _TASK_ID + 1
        self.id = str(_TASK_ID)
        self._runner = runner
        self._config = copy(config)
        self._parent = parent
        self._state = TaskState.INITIALIZED
        self.exception: Optional[BaseException] = None
        self.level: int = parent.level + 1 if parent else 0
        self._start_time: Optional[float] = None
        self._stop_time: Optional[float] = None

        runner.task_cache[self.id] = self
        runner.task_count += 1

    def __call__(self, *args, **kwargs):
        log.info("Starting task", task=self, id=self.id)
        self.state = TaskState.RUNNING
        self._runner.running_task_count += 1
        self._start_time = time.monotonic()
        try:
            timeout_s = None
            # Config can be something else than a dictionary
            if isinstance(self._config, dict):
                timeout_s = self._config.get("timeout", self.DEFAULT_TIMEOUT)
            # Zero means no timeout is desired
            if timeout_s and timeout_s > 0:
                log.debug("Running task with timeout", timeout=timeout_s)
                exception: Optional[Exception] = None
                try:
                    with Timeout(self._config.get("timeout", self.DEFAULT_TIMEOUT)):
                        return_val = None
                        while True:
                            try:
                                return_val = self._run(*args, **kwargs)
                            except ScenarioAssertionError as ex:
                                exception = ex
                                log.debug("Assertion failed, retrying...", ex=str(exception))

                            if return_val:
                                break

                            sleep(1)
                except Timeout:
                    self._runner.node_controller.send_debugging_signal()
                    log.debug("Timeout reached", ex=str(exception))
                    if exception:
                        raise exception
            else:
                return_val = self._run(*args, **kwargs)
        except BaseException as ex:
            self.state = TaskState.ERRORED
            log.exception("Task errored", task=self)
            self.exception = ex
            raise
        finally:
            self._stop_time = time.monotonic()
            self._runner.running_task_count -= 1

        runtime = self._stop_time - self._start_time
        log.info("Task successful", id=self.id, task=self, runtime=runtime)
        self.state = TaskState.FINISHED
        return return_val

    def _run(self, *args, **kwargs):  # pylint: disable=unused-argument,no-self-use
        gevent.sleep(1)

    def __repr__(self):
        return f"<{self.__class__.__name__}: {self._config}>"

    def __str__(self):
        color = TASK_STATE_COLOR[self.state]
        reset = click.termui._ansi_reset_all
        return (
            f'{" " * self.level * 2}- [{color}{self.state.value}{reset}] '
            f'{color}{self.__class__.__name__.replace("Task", "")}{reset}'
            f"{self._duration}{self._str_details}"
        )

    @property
    def urwid_label(self):
        task_state_style = f"task_state_{self.state.name.lower()}"
        duration = self._duration
        label = [
            ("default", "["),
            (task_state_style, self.state.value),
            ("default", "] "),
            (task_state_style, self.__class__.__name__.replace("Task", "")),
        ]
        if duration:
            label.append(("task_duration", self._duration))
        label.extend(self._urwid_details)
        return label

    def __hash__(self) -> int:
        return hash((self._config, self._parent))

    @property
    def _str_details(self):
        return f": {self._config}"

    @property
    def _urwid_details(self):
        return [": ", str(self._config)]

    @property
    def _duration(self):
        duration = 0.0
        if self._start_time:
            if self._stop_time:
                duration = self._stop_time - self._start_time
            else:
                duration = time.monotonic() - self._start_time
        if duration:
            return " " + str(timedelta(seconds=duration))
        return ""

    @property
    def done(self):
        return self.state in {TaskState.FINISHED, TaskState.ERRORED}

    @property
    def state(self):
        return self._state

    @state.setter
    def state(self, new_state):
        self._state = new_state
        self._runner.task_state_changed(self, self._state)


def get_task_class_for_type(task_type: str) -> Type[Task]:
    task_class = NAME_TO_TASK.get(task_type)
    if not task_class:
        raise UnknownTaskTypeError(f'Task type "{task_type}" is unknown.')
    return task_class


def register_task(task_name, task):
    global NAME_TO_TASK
    NAME_TO_TASK[task_name] = task


def collect_tasks(module):
    # If module is a package, discover inner packages / submodules
    for sub_module in pkgutil.iter_modules(path=module.__path__):
        _, sub_module_name, _ = sub_module
        sub_module_name = module.__name__ + "." + sub_module_name
        submodule = importlib.import_module(sub_module_name)
        collect_tasks_from_submodule(submodule)


def collect_tasks_from_submodule(submodule):
    for _, member in inspect.getmembers(submodule, inspect.isclass):
        if inspect.ismodule(member):
            collect_tasks(submodule)
            continue
        base_classes = inspect.getmro(member)
        if Task in base_classes and hasattr(member, "_name"):
            register_task(member._name, member)

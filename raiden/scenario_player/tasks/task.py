import time

from abc import abstractmethod


RUNNING = object()
ERROR = object()
FINISHED = object()


class Task:
    def __init__(self, stage, abort_on_fail=True, **config):
        self.abort_on_fail = abort_on_fail
        self.stage = stage
        self.config = config

    def __hash__(self):
        return hash(self.name)

    def __enter__(self):
        self.state = RUNNING
        self.stage.running_tasks += 1
        self._started_at = time.monotonic()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._ended_at = time.monotonic()
        self.stage.running_tasks -= 1
        if self.state is RUNNING:
            self.state = FINISHED

        if exc_type:
            self.state = ERROR
            self.exception = exc_val
            if self.abort_on_fail:
                # Returning no value causes the exception to be propagated upwards.
                return
        return self

    @classmethod
    def select(cls, task_type_name: str):
        """Select and return the appropriate Task class for the given task type."""

    @property
    def name(self):
        return self.__class__.__qualname__

    @property
    def exec_time(self):
        """Return the total execution duration of the task's __call__ method."""
        if self._start_time:
            if self._stop_time:
                return self._stop_time - self._start_time
            return time.monotonic() - self._start_time
        return None

    @property
    def done(self):
        pass

    @abstractmethod
    def execute(self):
        pass

    def register(self):
        """Register this Task instance with the scenario player environment."""
        pass


class RESTRequest(Task):
    METHOD = 'GET'




import pytest

from scenario_player import tasks
from scenario_player.tasks.base import collect_tasks, get_task_class_for_type, Task
from scenario_player.tasks.channels import TransferTask

pytest.register_assert_rewrite("tests.unittests.tasks.utils")


@pytest.fixture(scope="session", autouse=True)
def _collect_tasks():
    collect_tasks(tasks)


@pytest.fixture(scope="session", autouse=True)
def _reset_sync_waits():
    # No need for synchronization in the tests
    Task.SYNCHRONIZATION_TIME_SECONDS = 0


@pytest.fixture
def api_task_by_name(dummy_scenario_runner):
    def get_task(task_type, config):
        task_class = get_task_class_for_type(task_type)
        if issubclass(task_class, TransferTask):
            task_class._transfer_count = 0
        return task_class(runner=dummy_scenario_runner, config=config)

    return get_task

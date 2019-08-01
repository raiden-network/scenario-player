from __future__ import annotations

from collections import defaultdict

import pytest
import requests
import responses

from scenario_player import tasks
from scenario_player.tasks.base import collect_tasks, get_task_class_for_type
from scenario_player.tasks.channels import TransferTask


class DummyScenarioRunner:
    def __init__(self, scenario_name, token_address):
        self.scenario_name = scenario_name
        self.token_address = token_address
        self.session = requests.Session()
        self.task_cache = {}
        self.task_storage = defaultdict(dict)
        self.task_count = 0
        self.running_task_count = 0
        self.run_number = 0
        self.protocol = "http"

    def task_state_changed(self, task, new_state):
        pass

    def get_node_baseurl(self, index):
        return f"{index}"

    def get_node_address(self, index):
        return f"0x2{index:039d}"


@pytest.fixture(scope="session", autouse=True)
def _collect_tasks():
    collect_tasks(tasks)


@pytest.fixture
def mocked_responses():
    with responses.RequestsMock() as requests_mock:
        yield requests_mock


@pytest.fixture
def dummy_scenario_runner(mocked_responses):
    return DummyScenarioRunner("dummy_scenario", f"0x1{1:039d}")


@pytest.fixture
def api_task_by_name(dummy_scenario_runner):
    def get_task(task_type, config):
        task_class = get_task_class_for_type(task_type)
        if issubclass(task_class, TransferTask):
            task_class._transfer_count = 0
        return task_class(runner=dummy_scenario_runner, config=config)

    return get_task

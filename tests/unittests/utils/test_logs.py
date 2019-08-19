import pytest

from scenario_player.utils.logs import (
    pack_n_latest_logs_for_scenario_in_dir,
    pack_n_latest_node_logs_in_dir,
    verify_scenario_log_dir,
)



@pytest.fixture
def scenario_dir(tmp_path):
    scenario_dir = tmp_path.joinpath("test_scenario")
    scenario_dir.mkdir()
    return scenario_dir


@pytest.fixture(autouse=True)
def faked_scenario_dir(scenario_dir):

    # Create 10 fake scenario run logs, and 3 fake node folders per run
    for n in range(10):
        scenario_dir.joinpath(f"{scenario_dir.stem}-run_2000-08-{n}.log").touch()
        scenario_dir.joinpath(f"node_{n}_001").mkdir()
        scenario_dir.joinpath(f"node_{n}_002").mkdir()
        scenario_dir.joinpath(f"node_{n}_003").mkdir()

    # Create the run_num text file.
    run_num_file = scenario_dir.joinpath("run_num.txt")
    run_num_file.touch()
    run_num_file.write_text("9")


class TestPackNLatestNodeLogsInDir:
    @pytest.mark.parametrize(
        "given, expected",
        argvalues=[(0, 0), (100, 30), (5, 15), (10, 30)],
        ids=[
            "n=0 returns empty list",
            "n>current run number returns all available",
            "n<run num returns n paths",
            "n==run num returns n",
        ],
    )
    def test_func_returns_expected_number_of_paths(self, given, expected, scenario_dir):
        result = pack_n_latest_node_logs_in_dir(scenario_dir, given)
        assert len(result) == expected

    def test_func_returns_directories_only(self, scenario_dir):
        result = pack_n_latest_node_logs_in_dir(scenario_dir, 10)
        assert all(path.is_dir() for path in result)


class TestPackNLatestLogsForScenarioInDir:
    @pytest.mark.parametrize(
        "given, expected",
        argvalues=[(0, 0), (100, 10), (5, 5), (10, 10)],
        ids=[
            "n=0 returns empty list",
            "n>current run number returns all available",
            "n<run num returns n paths",
            "n==run num returns n",
        ],
    )
    def test_func_returns_expected_number_of_files(self, given, expected, scenario_dir):
        result = pack_n_latest_logs_for_scenario_in_dir(scenario_dir.name, scenario_dir, given)
        assert len(result) == expected

    def test_func_returns_files_only(self, scenario_dir):
        result = pack_n_latest_logs_for_scenario_in_dir(scenario_dir.name, scenario_dir, 10)
        assert all(path.is_file() for path in result)

    def test_func_raises_runtimeerror_if_no_logs_are_found(self, scenario_dir):
        # remove created log files.
        for path in scenario_dir.iterdir():
            if path.is_file():
                path.unlink()

        with pytest.raises(RuntimeError):
            pack_n_latest_logs_for_scenario_in_dir(scenario_dir.name, scenario_dir, 1)


class TestVerifyScenarioLogDir:
    def test_func_raises_not_a_directory_if_scenario_log_dir_is_not_a_directory(self, tmp_path):
        f = tmp_path.joinpath("scenarios")
        f.mkdir(parents=True)
        f= f.joinpath("wolohoo")
        f.write_text("something")
        with pytest.raises(NotADirectoryError):
            verify_scenario_log_dir("wolohoo", tmp_path)

    def test_func_raises_file_not_found_if_log_dir_does_not_exist(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            verify_scenario_log_dir("wolohoo", tmp_path)

    def test_func_returns_exepcted_paths(self, tmp_path):
        f = tmp_path.joinpath("scenarios", "test_scenario")
        f.mkdir(parents=True)
        scenarios_dir, log_dir = verify_scenario_log_dir("test_scenario", tmp_path)
        assert scenarios_dir == tmp_path.joinpath("scenarios")
        assert log_dir == tmp_path.joinpath("scenarios", "test_scenario")
from pathlib import Path
from typing import List


def pack_n_latest_node_logs_in_dir(scenario_dir: Path, n: int) -> List[Path]:
    """Return the node log folder paths for the `n` last runs."""
    if n == 0:
        return []
    # Get the number of runs that have been conducted
    run_num_file = scenario_dir.joinpath("run_num.txt")
    latest_run = 0
    if run_num_file.exists():
        latest_run = int(run_num_file.read_text())

    # Run count starts at 0
    num_of_runs = latest_run + 1

    # Avoid negative indices.
    earliest_run_to_pack = max(num_of_runs - n, 0)

    folders = []
    for run_num in range(earliest_run_to_pack, num_of_runs):
        for path in scenario_dir.iterdir():
            if not path.is_dir() or not path.name.startswith(f"node_{run_num}_"):
                continue
            folders.append(path)

    return folders


def pack_n_latest_logs_for_scenario_in_dir(scenario_name, scenario_log_dir: Path, n) -> List[Path]:
    """ List the `n` newest scenario log files in the given `scenario_log_dir`."""
    if n == 0:
        return []
    # Get all scenario run logs, sort and reverse them (newest first)
    scenario_logs = [
        path for path in scenario_log_dir.iterdir() if (path.is_file() and "-run_" in path.name)
    ]
    history = sorted(scenario_logs, reverse=True)

    # Can't pack more than the number of available logs.
    num_of_packable_iterations = min(n, len(scenario_logs))
    print(scenario_logs)
    print(n, len(scenario_logs), num_of_packable_iterations)

    if not history:
        raise RuntimeError(f"No Scenario logs found in {scenario_log_dir}")

    if num_of_packable_iterations < n:
        # We ran out of scenario logs to add before reaching the requested number of n latest logs.
        print(
            f"Only packing {num_of_packable_iterations} logs of requested latest {n} "
            f"- no more logs found for {scenario_name}!"
        )

    return history[:num_of_packable_iterations]


def verify_scenario_log_dir(scenario_name, data_path: Path):
    # The logs are located at .raiden/scenario-player/scenarios/<scenario-name>
    # - make sure the path exists.
    scenarios_dir = data_path.joinpath("scenarios")
    scenario_log_dir = scenarios_dir.joinpath(scenario_name)
    if not scenario_log_dir.exists():
        raise FileNotFoundError(
            f"No log directory found for scenario {scenario_name} at {scenario_log_dir}"
        )
    if not scenario_log_dir.is_dir():
        raise NotADirectoryError(f"Scenario Log path {scenario_log_dir} is not a directory!")
    return scenarios_dir, scenario_log_dir

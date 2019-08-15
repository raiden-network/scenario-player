from pathlib import Path
from typing import List


def pack_n_latest_node_logs_in_dir(scenario_dir: Path, n: int) -> List[Path]:
    """Return the node log folder paths for the `n` last runs."""
    # Get the number of runs that have been conducted
    run_num_file = scenario_dir.joinpath("run_number.txt")
    latest_run = 0
    if run_num_file.exists():
        latest_run = int(run_num_file.read_text())

    # Run count starts at 0
    num_of_runs = latest_run + 1

    # Avoid negative indices.
    earliest_run_to_pack = max(num_of_runs - n, 0)

    folders = []
    for run_num in range(earliest_run_to_pack, num_of_runs):
        print("Collecting")
        for path in scenario_dir.iterdir():
            if not path.is_dir() or not path.name.startswith(f"node_{run_num}_"):
                continue
            folders.append(path)

    return folders


def pack_n_latest_logs_for_scenario_in_dir(scenario_name, scenario_log_dir: Path, n) -> List[Path]:
    """ List the `n` newest scenario log files in the given `scenario_log_dir`."""
    # Get all scenario run logs, sort and reverse them (newest first)
    scenario_logs = [
        path for path in scenario_log_dir.iterdir() if (path.is_file() and "-run_" in path.name)
    ]
    history = sorted(scenario_logs, reverse=True)

    # Can't pack more than the number of available logs.
    num_of_packable_iterations = max(n, len(scenario_logs))

    if not history:
        raise RuntimeError(f"No Scenario logs found in {scenario_log_dir}")

    if num_of_packable_iterations < n:
        # We ran out of scenario logs to add before reaching the requested number of n latest logs.
        print(
            f"Only packing {num_of_packable_iterations} logs of requested latest {n} "
            f"- no more logs found for {scenario_name}!"
        )

    return history[:num_of_packable_iterations]

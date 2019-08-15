def pack_n_latest_logs_for_scenario_in_dir(scenario_name, scenario_log_dir: Path, n) -> List[Path]:
    """ Add the `n` latest log files for ``scenario_name`` in ``scenario_dir`` to a :cls:``set``
        and return it.
    """
    scenario_logs = [
        path for path in scenario_log_dir.iterdir() if (path.is_file() and "-run_" in path.name)
    ]
    history = sorted(scenario_logs, key=lambda x: x.stat().st_mtime, reverse=True)

    # Can't pack more than the number of available logs.
    num_of_packable_iterations = n or len(scenario_logs)

    if not history:
        raise RuntimeError(f"No Scenario logs found in {scenario_log_dir}")

    if num_of_packable_iterations < n:
        # We ran out of scenario logs to add before reaching the requested number of n latest logs.
        print(
            f"Only packing {num_of_packable_iterations} logs of requested latest {n} "
            f"- no more logs found for {scenario_name}!"
        )

    return history[:num_of_packable_iterations]

def extract_action(dest, parser):
    for action in parser._actions:
        if action.dest == dest:
            return action
    raise AssertionError(f"No flag with dest {dest} in parser!")

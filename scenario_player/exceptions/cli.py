from scenario_player.exceptions import ScenarioError


class WrongPassword(ScenarioError):
    """
    Generic Error that gets raised if eth_keystore raises ValueError("MAC mismatch")
    Usually that's caused by an invalid password
    """

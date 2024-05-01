import os


EFFECTOR_STATUS: str = str(os.environ.get("EFFECTOR_STATUS", False))


def get_effector(effector: bool) -> list:
    if effector:
        return [effector, EFFECTOR_STATUS]
    else:
        return [effector]

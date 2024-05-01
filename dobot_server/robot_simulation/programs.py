import ast
import os
import random
import time
from typing import Tuple

import pandas

from dobot_server.utils import get_effector


PROBABILITY_RANGE: int = int(os.environ.get("PROBABILITY_RANGE", 10000))
ALARM_CLEARED: int = int(os.environ.get("ALARM_CLEARED", 900))
ALARMS_RANGE: int = int(os.environ.get("ALARMS_RANGE", 20))


class RobotStatus:
    def __init__(self, pose, alarm, work_status, laser, suction_cup, gripper,
                 runtime, alarm_timer):
        self.pose = pose
        self.alarm = alarm
        self.work_status = work_status
        self.laser = get_effector(laser)
        self.suction_cup = get_effector(suction_cup)
        self.gripper = get_effector(gripper)
        self.runtime = runtime
        self.alarm_timer = alarm_timer


def get_program_data(file: str) -> ...:
    return pandas.read_csv(os.path.abspath(file), delimiter="\t")


def get_first_pose(robot) -> str:
    data = get_program_data(robot.program_path)
    pose = ast.literal_eval(data.iloc[0, 0])
    angle = ast.literal_eval(data.iloc[0, 1])
    pose.append(angle)
    return f"{pose}"


def losing_step_alarm() -> ...:
    if random.randint(1, 100*PROBABILITY_RANGE) == 1:
        return 0x50
    if random.randint(1, 100*PROBABILITY_RANGE) == 2:
        return 0x51
    if random.randint(1, 100*PROBABILITY_RANGE) == 3:
        return 0x52
    if random.randint(1, 100*PROBABILITY_RANGE) == 4:
        return 0x53
    return False


# Movement limits:
# coordinates[0]: [-50, 350], coordinates[1]: [-50, 350],
# coordinates[2]: [-200, 200], coordinates[-130, 130]
def motion_inverse_resolve_alarm(coordinates: list[int]) -> bool:
    if (
            coordinates[0] > 347
            or coordinates[0] < -47
            or coordinates[1] > 347
            or coordinates[1] < -47
            or coordinates[2] > 197
            or coordinates[2] < -197
            or coordinates[3] > 128
            or coordinates[3] < -128
    ):
        alert = random.randint(1, PROBABILITY_RANGE)
        if alert == PROBABILITY_RANGE:
            return True

    return False


# Joint limits:
# joints[0]: [-90, 90], joints[1]: [0, 85],
# joints[2]: [-10, 90], joints[-90, 90]
def inverse_resolve_alarm(joints: list[int]) -> bool:
    if (
            joints[0] > 88
            or joints[0] < -88
            or joints[1] > 82
            or joints[1] < 3
            or joints[2] > 88
            or joints[2] < -3
            or joints[3] > 88
            or joints[3] < -88
    ):
        alert = random.randint(1, PROBABILITY_RANGE)
        if alert == PROBABILITY_RANGE:
            return True

    return False


def get_alarm(robot) -> Tuple[int, float]:
    pose = ast.literal_eval(robot.pose)
    joints = pose[4]

    # Inverse resolve alert
    if inverse_resolve_alarm(joints):
        return 0x12, time.time()

    if motion_inverse_resolve_alarm(pose):
        return 0x21, time.time()

    step_alarm = losing_step_alarm()
    if step_alarm:
        return step_alarm, time.time()

    # Return no alarm
    return 0x00, 0.0


def calc_status(robot):

    # Load robot_simulation status
    result: RobotStatus = RobotStatus(robot.pose, robot.alarm,
                                      robot.work_status, robot.laser,
                                      robot.suction_cup, robot.gripper,
                                      robot.runtime, robot.alarm_timer)

    # Check alarms
    if robot.alarm != 0x00:
        print(time.time() - robot.alarm_timer)
        if (time.time() - robot.alarm_timer) > ALARM_CLEARED:
            if random.randint(1, ALARMS_RANGE) == ALARMS_RANGE:
                result.work_status = True
                result.alarm = 0x00
    if not result.work_status:
        return result

    # Get runtime
    result.runtime = time.time() - robot.timer
    while result.runtime > robot.program_runtime:
        result.runtime = result.runtime - robot.program_runtime
    data = get_program_data(robot.program_path)
    position = int(result.runtime // robot.speed)

    # Get new pose
    pose = ast.literal_eval(data.iloc[position, 0])
    angle = ast.literal_eval(data.iloc[position, 1])
    pose.append(angle)
    result.pose = str(pose)

    # Get effectors statuses
    if robot.laser[0]:
        laser_status = [robot.laser[0], data.iloc[position, 2]]
        result.laser = laser_status
    if robot.suction_cup[0]:
        suction_cup_status = [robot.suction_cup[0], data.iloc[position, 3]]
        result.suction_cup = suction_cup_status
    if robot.gripper[0]:
        gripper_status = [robot.gripper[0], data.iloc[position, 4]]
        result.gripper = gripper_status

    # Checking if alarm could be fired
    result.alarm, result.alarm_timer = get_alarm(robot)
    if result.alarm != 0x00:
        result.work_status = False

    return result

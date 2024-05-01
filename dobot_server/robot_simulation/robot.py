import os
import time

from dobot_server.utils import get_effector
from dobot_server.robot_simulation import programs

DEFAULT_WORK_STATUS: bool = bool(os.getenv("DEFAULT_WORK_STATUS", True))
default_alarm = 0x00
status = False


class Robot:
    def __init__(
        self,
        label,
        robot_id,
        sn,
        version,
        program,
        name,
        laser,
        suction_cup,
        gripper,
        program_path,
        program_time
    ):
        # Values not available for clients
        self.program_path = program_path
        self.program_lines = self.get_program_lines()
        self.program_runtime = program_time
        self.runtime = 0
        self.timer = time.time()
        self.speed = self.get_speed()
        self.alarm_timer = 0
        # Values for clients
        self.label = label
        self.sn = sn
        self.version = version
        self.id = robot_id
        self.name = name
        self.home = self.get_home()
        self.pose = self.home
        self.alarm = default_alarm
        self.program = program
        self.work_status = DEFAULT_WORK_STATUS
        self.laser = get_effector(laser)
        self.suction_cup = get_effector(suction_cup)
        self.gripper = get_effector(gripper)

    def get_home(self) -> str:
        self.home = programs.get_first_pose(self)
        return self.home

    def change_work_status(self, new_work_status: bool):
        self.work_status = new_work_status
        self.new_status()
        return

    def get_program_lines(self) -> int:
        # file = os.path.abspath(self.program_path)
        with open(self.program_path, "r") as f:
            lines = len(f.readlines()) - 1
        return lines

    def get_speed(self) -> float:
        return self.program_runtime / self.program_lines

    def new_status(self):
        new_status: programs.RobotStatus = programs.calc_status(self)
        self.pose = new_status.pose
        self.alarm = new_status.alarm
        self.work_status = new_status.work_status
        self.runtime = new_status.runtime
        self.alarm_timer = new_status.alarm_timer
        self.laser = new_status.laser
        self.suction_cup = new_status.suction_cup
        self.gripper = new_status.gripper

        return

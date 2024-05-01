import asyncio
import dataclasses
import logging
import os
import re
import socket
import time

import yaml

from asyncua import Server, ua
from asyncua.common.methods import uamethod
from asyncua.crypto.cert_gen import setup_self_signed_certificate
from asyncua.server.user_managers import CertificateUserManager
from cryptography.x509.oid import ExtendedKeyUsageOID
from logging.handlers import RotatingFileHandler
from pathlib import Path

from dobot_server.robot_simulation import robot as r


CONFIG_FILE: str = str(os.environ.get("CONFIG_FILE"))
if CONFIG_FILE is None:
    raise RuntimeError("Config file was not specified")
robots = []
server_robots = {}


def setup_logger():
    logger = logging.getLogger("asyncua.uaprocessor")
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    # file_handler = RotatingFileHandler(
    #     "server.log", maxBytes=5 * 1024 * 1024, backupCount=2
    # )
    file_handler = RotatingFileHandler("server.log")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    console_handler = logging.StreamHandler()

    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


_logger = setup_logger()


@dataclasses.dataclass(frozen=True)
class ServerConfig:
    server_name: str
    server_app_uri: str
    server_address: str
    server_endpoint: str
    robots_url: str
    log_server_url: str
    security_policy: list
    country_name: str
    state_or_province_name: str
    locality_name: str
    organization_name: str
    refresh_rate: int

    @classmethod
    def from_dict(cls, data: dict) -> "ServerConfig":
        return cls(**data)


@dataclasses.dataclass(frozen=True)
class RobotConfig:
    label: str
    serial_number: str
    id: int
    name: str
    program: int
    version: str
    laser: bool
    suction_cup: bool
    gripper: bool

    @classmethod
    def from_dict(cls, data: dict) -> "RobotConfig":
        return cls(**data)


@dataclasses.dataclass(frozen=True)
class ProgramsConfig:
    program: int
    path: str
    time_length: int

    @classmethod
    def from_dict(cls, data: dict) -> "ProgramsConfig":
        return cls(**data)


@dataclasses.dataclass(frozen=True)
class Config:
    server: ServerConfig
    programs: list[ProgramsConfig]
    robots: list[RobotConfig]

    @classmethod
    def from_dict(cls, data: dict) -> "Config":
        return cls(
            server=ServerConfig.from_dict(data["server"]),
            programs=[ProgramsConfig.from_dict(p) for p in data["programs"]],
            robots=[RobotConfig.from_dict(rob) for rob in data["robots"]],
        )


@uamethod
def stop_robot(node, value: str):
    changed = []
    values = re.split(r",+\s+|,+|\s+", value)
    for value in values:
        for robot in robots:
            if robot.label == value:
                if robot.work_status:
                    robot.change_work_status(False)
                    _logger.info(f"Robot {robot.label} stopped")
                    changed.append(value)
    return f"{changed}"


@uamethod
def stop_robots(node):
    for robot in robots:
        if robot.work_status:
            robot.change_work_status(False)
            _logger.info(f"Robot {robot.label} stopped")
    return 0


@uamethod
def resume_robot(node, value: str):
    changed = []
    values = re.split(r",+\s+|,+|\s+", value)
    for value in values:
        for robot in robots:
            if robot.label == value:
                if not robot.work_status:
                    robot.change_work_status(True)
                    _logger.info(f"Robot {robot.label} resumed")
                    changed.append(value)
    return f"{changed}"


@uamethod
def resume_robots(node):
    for robot in robots:
        if not robot.work_status:
            robot.change_work_status(True)
            _logger.info(f"Robot {robot.label} resumed")
    return 0


@uamethod
async def get_realtime_pose(node, value):
    values = re.split(r",+\s+|,+|\s+", value)
    if not values:
        return "Wrong format"
    if len(values) > 1:
        return "Only one object at a time"
    for robot in robots:
        if robot.label == values[0]:
            robot.new_status()
            return f"{robot.pose}"
    return "Something went wrong"


@uamethod
async def list_robots(node):
    result = []
    for robot in server_robots:
        result.append(robot)
    return f"{result}"


async def add_robot(robots_idx, server, robot) -> dict:
    # Values for observation
    robot_node = await server.nodes.objects.add_object(robots_idx, robot.label)
    robot_id = await robot_node.add_variable(robots_idx, f"id_{robot.label}", robot.id)
    robot_sn = await robot_node.add_variable(robots_idx, f"sn_{robot.label}", robot.sn)
    robot_name = await robot_node.add_variable(
        robots_idx, f"name_{robot.label}", robot.name
    )
    robot_version = await robot_node.add_variable(
        robots_idx, f"version_{robot.label}", robot.version
    )
    robot_program = await robot_node.add_variable(
        robots_idx, f"program_{robot.label}", robot.program
    )
    robot_pose = await robot_node.add_variable(
        robots_idx, f"pose_{robot.label}", robot.pose
    )
    robot_alarm = await robot_node.add_variable(
        robots_idx, f"alarm_{robot.label}", robot.alarm
    )
    robot_home = await robot_node.add_variable(
        robots_idx, f"home_position_{robot.label}", robot.home
    )
    robot_status = await robot_node.add_variable(
        robots_idx, f"work_status_{robot.label}", robot.work_status
    )
    robot_laser = await robot_node.add_variable(
        robots_idx, f"laser_{robot.label}", f"{robot.laser}"
    )
    robot_suction_cup = await robot_node.add_variable(
        robots_idx, f"suction_cup_{robot.label}", f"{robot.suction_cup}"
    )
    robot_gripper = await robot_node.add_variable(
        robots_idx, f"gripper_{robot.label}", f"{robot.gripper}"
    )

    return {
        "node": robot_node,
        "id": robot_id,
        "name": robot_name,
        "sn": robot_sn,
        "version": robot_version,
        "program": robot_program,
        "pose": robot_pose,
        "alarm": robot_alarm,
        "home": robot_home,
        "status": robot_status,
        "laser": robot_laser,
        "suction_cup": robot_suction_cup,
        "gripper": robot_gripper,
    }


async def add_robots(robots_idx, server):
    for robot in robots:
        server_robot = await add_robot(robots_idx, server, robot)
        server_robots[robot.label] = server_robot
    return


def create_robot(config: list[RobotConfig], program: list[ProgramsConfig]):
    for c in config:
        p_config = [p for p in program if p.program == c.program]
        robot = r.Robot(
            label=c.label,
            robot_id=c.id,
            sn=c.serial_number,
            version=c.version,
            program=c.program,
            name=c.name,
            laser=c.laser,
            suction_cup=c.suction_cup,
            gripper=c.gripper,
            program_path=p_config[0].path,
            program_time=p_config[0].time_length
        )
        robots.append(robot)
    return


def get_security_policy(policy_names: list) -> ...:
    policy = []
    try:
        for policy_name in policy_names:
            if policy_name == "Basic256Sha256_SignAndEncrypt":
                policy.append(
                    ua.SecurityPolicyType.Basic256Sha256_SignAndEncrypt
                )
            elif policy_name == "Basic256Sha256_Sign":
                policy.append(ua.SecurityPolicyType.Basic256Sha256_Sign)
            elif policy_name == "Basic128Rsa15_SignAndEncrypt":
                policy.append(
                    ua.SecurityPolicyType.Basic128Rsa15_SignAndEncrypt
                )
            elif policy_name == "Basic128Rsa15_Sign":
                policy.append(ua.SecurityPolicyType.Basic128Rsa15_Sign)
            elif policy_name == "Aes128Sha256RsaOaep_SignAndEncrypt":
                policy.append(
                    ua.SecurityPolicyType.Aes128Sha256RsaOaep_SignAndEncrypt
                )
            elif policy_name == "Aes128Sha256RsaOaep_Sign":
                policy.append(ua.SecurityPolicyType.Aes128Sha256RsaOaep_Sign)
            elif policy_name == "Basic256_SignAndEncrypt":
                policy.append(ua.SecurityPolicyType.Basic256_SignAndEncrypt)
            elif policy_name == "Basic256_Sign":
                policy.append(ua.SecurityPolicyType.Basic256_Sign)
    finally:
        return policy


async def main():
    # _logger = setup_logger()

    if os.path.exists("files/certificates/server.crt"):
        os.remove("files/certificates/server.crt")
    if os.path.exists("files/certificates/server.pem"):
        os.remove("files/certificates/server.pem")

    with open(os.path.abspath(CONFIG_FILE)) as f:
        raw_config = yaml.safe_load(f)
    config = Config.from_dict(raw_config)

    # Set up user_manager and server
    if config.server.security_policy:
        cert_user_manager = CertificateUserManager()
        admin_cert = Path(os.path.abspath("files/certificates/admin.crt"))
        await cert_user_manager.add_user(admin_cert, name="admin")
        server = Server(user_manager=cert_user_manager)
    else:
        server = Server()

    await server.init()
    server.set_endpoint(config.server.server_endpoint)
    server.set_server_name(config.server.server_name)

    # Set up namespace for log server
    log_uri = config.server.log_server_url
    log_idx = await server.register_namespace(log_uri)
    # Set up namespace for robotic arms
    robots_uri = config.server.robots_url
    robots_idx = await server.register_namespace(robots_uri)

    # Set server security
    policy = get_security_policy(config.server.security_policy)

    if policy:
        country = config.server.country_name
        state = config.server.state_or_province_name
        locality = config.server.locality_name
        organization = config.server.organization_name
        server.set_security_policy(policy)
        _logger.info(f"Server security policy set to: {policy}")
        host_name = socket.gethostname()
        server_api_uri = f"{config.server.server_app_uri}@{host_name}"
        server_cert = Path(os.path.abspath("files/certificates/server.crt"))
        server_key = Path(os.path.abspath("files/certificates/server.pem"))
        await setup_self_signed_certificate(
            server_key,
            server_cert,
            server_api_uri,
            host_name,
            [ExtendedKeyUsageOID.CLIENT_AUTH, ExtendedKeyUsageOID.SERVER_AUTH],
            {
                "countryName": f"{country}",
                "stateOrProvinceName": f"{state}",
                "localityName": f"{locality}",
                "organizationName": f"{organization}",
            },
        )
        # Load server certificate and private key
        await server.load_certificate(str(server_cert))
        await server.load_private_key(str(server_key))
    else:
        _logger.warning("None security policy has been set!")

    # Create robots
    create_robot(config.robots, config.programs)
    # Add robots to server
    await add_robots(robots_idx, server)

    # Add methods
    # Add method for stopping one and more robots
    await server.nodes.objects.add_method(
        ua.NodeId("stop_robot", robots_idx),
        ua.QualifiedName("stop_robot", robots_idx),
        stop_robot,
        [ua.VariantType.String],
        [ua.VariantType.String],
    )
    # Add method for stopping all robots
    await server.nodes.objects.add_method(
        ua.NodeId("stop_all_robots", robots_idx),
        ua.QualifiedName("stop_all_robots", robots_idx),
        stop_robots,
        [ua.VariantType.Null],
        [ua.VariantType.Int16],
    )
    # Add method for resuming one and more robots
    await server.nodes.objects.add_method(
        ua.NodeId("resume_robot", robots_idx),
        ua.QualifiedName("resume_robot", robots_idx),
        resume_robot,
        [ua.VariantType.String],
        [ua.VariantType.String],
    )
    # Add method for resuming all robots
    await server.nodes.objects.add_method(
        ua.NodeId("resume_all_robots", robots_idx),
        ua.QualifiedName("resume_all_robots", robots_idx),
        resume_robots,
        [ua.VariantType.Null],
        [ua.VariantType.Int16],
    )
    # Add method for getting real time pose
    await server.nodes.objects.add_method(
        ua.NodeId("realtime_pose", robots_idx),
        ua.QualifiedName("realtime_pose", robots_idx),
        get_realtime_pose,
        [ua.VariantType.String],
        [ua.VariantType.String],
    )
    # Add method for listing all server robots
    await server.nodes.objects.add_method(
        ua.NodeId("list_robots", robots_idx),
        ua.QualifiedName("list_robots", robots_idx),
        list_robots,
        [ua.VariantType.Null],
        [ua.VariantType.String],
    )

    _logger.info("Starting server!")

    refresh_rate = config.server.refresh_rate
    if refresh_rate is None:
        refresh_rate = 1

    async with server:
        while True:
            for robot in robots:
                server_r = server_robots[robot.label]
                robot.new_status()

                await server_r["pose"].write_value(robot.pose)
                await server_r["alarm"].write_value(robot.alarm)
                await server_r["status"].write_value(robot.work_status)
                await server_r["laser"].write_value(f"{robot.laser}")
                await server_r["suction_cup"].write_value(f"{robot.suction_cup}")
                await server_r["gripper"].write_value(f"{robot.gripper}")

            _logger.debug(f"Sleeping {refresh_rate} seconds.")
            await asyncio.sleep(refresh_rate)


def amain():
    asyncio.run(main(), debug=True)


if __name__ == "__main__":
    amain()

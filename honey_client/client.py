import ast
import asyncio
import os
import sys

import yaml

from asyncua import Client, ua


config_file = "dobot_server/files/config.yaml"


def load_config(config_path):
    print(config_path)
    with open(config_path, "r") as config:
        config = yaml.full_load(config)
        return config["server"]


async def get_values(client, robots_idx, robot):
    identifier = await client.nodes.root.get_child(
        f"0:Objects/{robots_idx}:{robot}/{robots_idx}:id_{robot}"
    )
    identifier = await identifier.read_value()
    sn = await client.nodes.root.get_child(
        f"0:Objects/{robots_idx}:{robot}/{robots_idx}:sn_{robot}"
    )
    sn = await sn.read_value()
    name = await client.nodes.root.get_child(
        f"0:Objects/{robots_idx}:{robot}/{robots_idx}:name_{robot}"
    )
    name = await name.read_value()
    version = await client.nodes.root.get_child(
        f"0:Objects/{robots_idx}:{robot}/{robots_idx}:version_{robot}"
    )
    version = await version.read_value()
    program = await client.nodes.root.get_child(
        f"0:Objects/{robots_idx}:{robot}/{robots_idx}:program_{robot}"
    )
    program = await program.read_value()
    pose = await client.nodes.root.get_child(
        f"0:Objects/{robots_idx}:{robot}/{robots_idx}:pose_{robot}"
    )
    pose = await pose.read_value()
    alarm = await client.nodes.root.get_child(
        f"0:Objects/{robots_idx}:{robot}/{robots_idx}:alarm_{robot}"
    )
    alarm = await alarm.read_value()
    home = await client.nodes.root.get_child(
        f"0:Objects/{robots_idx}:{robot}/{robots_idx}:home_position_{robot}"
    )
    home = await home.read_value()
    status = await client.nodes.root.get_child(
        f"0:Objects/{robots_idx}:{robot}/{robots_idx}:work_status_{robot}"
    )
    status = await status.read_value()
    laser = await client.nodes.root.get_child(
        f"0:Objects/{robots_idx}:{robot}/{robots_idx}:laser_{robot}"
    )
    laser = await laser.read_value()
    suction_cup = await client.nodes.root.get_child(
        f"0:Objects/{robots_idx}:{robot}/{robots_idx}:suction_cup_{robot}"
    )
    suction_cup = await suction_cup.read_value()
    gripper = await client.nodes.root.get_child(
        f"0:Objects/{robots_idx}:{robot}/{robots_idx}:gripper_{robot}"
    )
    gripper = await gripper.read_value()

    print(f"id:             {identifier}\n"
          f"sn:             {sn}\n"
          f"name:           {name}\n"
          f"version:        {version}\n"
          f"program:        {program}\n"
          f"pose:           {pose}\n"
          f"alarm:          {alarm}\n"
          f"home:           {home}\n"
          f"status:         {status}\n"
          f"laser:          {laser}\n"
          f"suction_cup:    {suction_cup}\n"
          f"gripper:        {gripper}\n")


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


def print_menu():
    print(" ____________________________________________________\n"
          "|                                                    |\n"
          "|    01   Show robots                                |\n"
          "|    02   Show robot status                          |\n"
          "|    03   Stop robot(s) based on label               |\n"
          "|    04   Stop all robots                            |\n"                         
          "|    05   Resume robot(s)                            |\n"
          "|    06   Resume all robots                          |\n"
          "|    00   Exit                                       |\n"       
          "|____________________________________________________|\n")


async def main():
    config_path = f"{os.path.abspath("../")}/{config_file}"
    config = load_config(config_path)
    # server_address = config["server_address"]
    server_url = config["server_endpoint"]
    robots_url = config["robots_url"]

    print(f"Connection to {server_url} ...")

    client = Client(server_url)
    await client.connect()

    robots_idx = await client.get_namespace_index(robots_url)
    print(f"Namespace index to '{robots_url}': {robots_idx}")

    while True:
        print_menu()
        option = input("Enter your option: ")

        try:
            option = int(option)
        except ValueError:
            print("\nWrong value! Please insert a number of desired option.")
        match option:

            case 1:
                try:
                    result = await client.nodes.objects.call_method(
                        f"{robots_idx}:list_robots"
                    )
                    result = ast.literal_eval(result)
                    for robot in result:
                        print(robot)
                except (ConnectionError, ua.UaError):
                    print("Connection closed, trying reconnect...")
                    client = Client(server_url)
                    await client.connect()
                    continue
                except (RuntimeError, ua.UaError):
                    print("Request timeout")
                    continue
                except Exception as e:
                    print(f"Something went wrong: {e}")
                    continue
                continue

            case 2:
                robot = input("Enter robot label: ")
                try:
                    await get_values(client, robots_idx, robot)
                except ua.uaerrors.BadNoMatch:
                    print("Choose existing robot please.")
                    continue
                except (ConnectionError, ua.UaError):
                    print("Connection closed, trying reconnect...")
                    client = Client(server_url)
                    await client.connect()
                    continue
                except (RuntimeError, ua.UaError):
                    print("Request timeout")
                    continue
                except Exception as e:
                    print(f"Something went wrong: {e}")
                    continue
                continue

            case 3:
                label = input("Enter the labels of robots you want to stop: ")
                try:
                    result = await client.nodes.objects.call_method(
                        f"{robots_idx}:stop_robot", f"{label}"
                    )
                    result = ast.literal_eval(result)
                    if len(result) == 0:
                        print("No robot was stopped.")
                        continue
                    print("Stopped robots:")
                    for robot in result:
                        print(robot)
                except (ConnectionError, ua.UaError):
                    print("Connection closed, trying reconnect...")
                    client = Client(server_url)
                    await client.connect()
                    continue
                except (RuntimeError, ua.UaError):
                    print("Request timeout")
                    continue
                except Exception as e:
                    print(f"Something went wrong: {e}")
                    continue
                continue

            case 4:
                try:
                    result = await client.nodes.objects.call_method(
                        f"{robots_idx}:stop_all_robots"
                    )
                    if result != 0:
                        print("Something went wrong.")
                        continue
                    print("All robots are stopped.")
                except (ConnectionError, ua.UaError):
                    print("Connection closed, trying reconnect...")
                    client = Client(server_url)
                    await client.connect()
                    continue
                except (RuntimeError, ua.UaError):
                    print("Request timeout")
                    continue
                except Exception as e:
                    print(f"Something went wrong: {e}")
                    continue
                continue

            case 5:
                label = input("Enter the labels of robots you want to resume: ")
                try:
                    result = await client.nodes.objects.call_method(
                        f"{robots_idx}:resume_robot", f"{label}"
                    )
                    result = ast.literal_eval(result)
                    if len(result) == 0:
                        print("No robot was resumed.")
                        continue
                    print("Resumed robots:")
                    for robot in result:
                        print(robot)
                except (ConnectionError, ua.UaError):
                    print("Connection closed, trying reconnect...")
                    client = Client(server_url)
                    await client.connect()
                    continue
                except (RuntimeError, ua.UaError):
                    print("Request timeout")
                    continue
                except Exception as e:
                    print(f"Something went wrong: {e}")
                    continue
                continue

            case 6:
                try:
                    result = await client.nodes.objects.call_method(
                        f"{robots_idx}:resume_all_robots"
                    )
                    if result != 0:
                        print("Something went wrong.")
                        continue
                    print("Robots were resumed.")
                except (ConnectionError, ua.UaError):
                    print("Connection closed, trying reconnect...")
                    client = Client(server_url)
                    await client.connect()
                    continue
                except (RuntimeError, ua.UaError):
                    print("Request timeout")
                    continue
                except Exception as e:
                    print(f"Something went wrong: {e}")

                    continue
                continue

            case 0:
                sys.exit(0)
            case _:
                print("\nChose one of the options below:")
                continue


if __name__ == "__main__":
    asyncio.run(main())

# OPC-UA Honeypot

## About

## How to install
### Linux
#### 1. Using venv
```commandline
git clone git@github.com:jtydlack/OPC-UA_to_modbys_gateway.git
cd OPC-UA_to_modbys_gateway
python -m venv honey
source honey/bin/activate
pip install -r requirements.txt
```

## Configuration

All necessary configuration is done in [conf.yaml](dobot_server/files/config.yaml).
The file is separated into three parts: server, program and robots.

There is an example of easy config with just one small program and one robot.
Each od this part will be explained more:
```yaml
server:
  server_name: "Python-OPC-UA"
  server_address: "127.0.0.1"
  server_app_uri: "opcuaserver"
  server_endpoint: "opc.tcp://localhost:4840"
  robots_url: "http://myDobot.factory.com"
  log_server_url: "http://logserver.factory.com"
  refresh_rate: 6
  security_policy: [Basic256Sha256_SignAndEncrypt]
  country_name: "CZ"
  state_or_province_name: "state"
  locality_name: "locality"
  organization_name: "VUT"

programs:
  - program: 1
    path: "./robot_simulation/programs/program_1.yaml"
    time_length: 30

robots:
  - label: "robot_1"
    serial_number: A1234567890B
    id: 1000
    name: "Souta"
    program: 1
    version: "1.1.1.0"
    laser: True
    suction_cup: False
    gripper: False
```

### Server configuration

In this part of config you are setting basic configuration for server. There is
a simple example how the config could look like:
```yaml
server:
  server_name: "Python-OPC-UA"
  server_address: "127.0.0.1"
  server_app_uri: "opcuaserver"
  server_endpoint: "opc.tcp://localhost:4840"
  robots_url: "http://myDobot.factory.com"
  log_server_url: "http://logserver.factory.com"
  refresh_rate: 1
  security_policy:  [Basic256Sha256_SignAndEncrypt]
  country_name: "CZ"
  state_or_province_name: "state"
  locality_name: "locality"
  organization_name: "VUT"
```

`server_name: str` parameter is used to give specific name to server. Can be
an empty string.

`server_address: str` is parameter specifying ip of server. Can be an empty string.

`server_app_uri: str` is parameter used when creating certificates for server.
Can be an empty string.

`server_endpoint: str` address used to connect to the server. Must be filled.

`robots_url: str` address used for creating robots namespace, should be different
from log_server_uri. Can be an empty string.

`refresh_rate: int` parameter specifying often should server ask for new status
of robots. If empty default value is set to 1.

`security_policy: list` parameter specifying security policies of server.
In case you do not want to set any leave the list or parameter empty. Otherwise, 
there is a list of security policies which can be set (multiple at once can be set):
- Basic256Sha256_SignAndEncrypt
- Basic256Sha256_Sign
- Basic128Rsa15_SignAndEncrypt
- Basic128Rsa15_Sign
- Aes128Sha256RsaOaep_SignAndEncrypt
- Aes128Sha256RsaOaep_Sign
- Basic256_SignAndEncrypt
- Basic256_Sign

Parameters `country_name`,`state_or_province_name`, `locality_name` and 
`organization_name` are mandatory only when chosen security policy
for generating certificate.

### Program configuration

In this part of config you are setting up programs which can be loaded. You can
insert as many programs you wish, and you can also use any file multiple times
and just running it faster/slower by changing `time_length` parameter. There is 
an example how program config can look like.

```yaml
- program: 1
  path: "./robot_simulation/programs/program_1.yaml"
  time_length: 30
```

Each parameter is necessary.

`program: int` parameter is there to identify program, this parameter is than used
in robot config, so the robot knows where to get position statuses. There is
multiple templates of programs, but you can create your own,
instructions how the program file should look like are in this 
[chapter how to make program template](#how-to-make-program-template).

`path: str` parameter is specifying path to program file. There is multiple templates
you can use by default in [programs folder](dobot_server/files/programs).

`time_lenght: int` this is parameter specifying how fast should be one round of
program executed. Please make sure you are using reasonable time so the robotic
arm is not moving suspiciously fast.

### Robot(s) configuration

In this part you are specifying how many robots you want and their specifications.
This an example how configuration of robot can look like:

```yaml
- label: "robot_1"
  serial_number: "A1234567890B"
  id: 1000
  name: "Souta"
  program: 1
  version: "1.1.1.0"
  laser: True
  suction_cup: False
  gripper: False
```

`label: str` parameter is used for naming robot in server robot namespace, so it can
be addressed by the server or client by this name. It is necessary to use unique
label for each robot.

`serial_number: str` can be passed as a string or as a number, it is static parameter
and once it is set it cannot be changed.

`id: int` of a robot. This parameter should be unique, but it is not necessary for
the run of the server.

`name: str` again, should be unique, but it is not necessary for the run of the server,
can be same as a label.

`program: int` parameter identifying program you want to run on specific robot. Must
be same as one of selected programs in `programs` selection of the config file.
Multiple robots can have the same program.

`version: str` parameter is specifying version of robotic arm.

`laser: bool` parameter specified as True/False. It is enabling laser for robotic
arm, if set to False the arm cannot use laser even if it is set in program to True.
The same is applied to `susction_cup: bool` and `gripper: bool`.

## How to run

This server is supposed to be run in
[GitHub project honeynet](https://github.com/mnecas/honeynet) but probably can
be run in other project which are capable of running dockerized server as honeypot.

## How to make program template

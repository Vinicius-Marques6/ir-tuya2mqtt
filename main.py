import re
import os
import json
import logging
import dataclasses
import threading
from typing import List

import tinytuya
import paho.mqtt.client as mqtt

logger = logging.getLogger(__name__)
sh = logging.StreamHandler()
logger.addHandler(sh)
logger.setLevel(logging.INFO)

if os.environ.get('DEBUG'):
    logger.setLevel(logging.DEBUG)

if os.environ.get('TINYTUYA_DEBUG'):
    tinytuya.set_debug(True)

@dataclasses.dataclass
class Config:
    host: str = dataclasses.field(default="localhost")
    port: int = dataclasses.field(default=1883)
    topic: str = dataclasses.field(default="topic/")
    mqtt_user: str = dataclasses.field(default=None)
    mqtt_pass: str = dataclasses.field(default=None)

@dataclasses.dataclass
class Device:
    name: str
    id: str
    key: str
    ip: str
    version: float = dataclasses.field(default=3.3)
    tuya: tinytuya.Device = dataclasses.field(default=None)

def read_template_file(filename):
    data = {}
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            for line in f:
                parts = line.strip().split(" ", 1)
                if len(parts) == 2:
                    key, value = parts
                    data[key] = value
    except FileNotFoundError:
        logger.exception(f"Arquivo {filename} não encontrado.")
    return data

def read_config() -> Config:
    with open('config.json') as f:
        c = json.load(f)
    config = Config(c['host'],c['port'],c['topic'],c['mqtt_user'],c['mqtt_pass'])

    return config

def read_devices() -> List[Device]:
    '''
    Read devices from devices.json file
    '''
    with open('devices.json') as f:
        snapshot = json.load(f)
    devices = {}

    for d in snapshot:
        devices[d['id']] = Device(d['name'],d['id'],d['key'],d['ip'])
        if 'version' in d:
            devices[d['id']].version = d['version']

    return devices.values()

def on_connect(client, userdata, flags, reason_code, properties):
    '''
    On broker connected, subscribe to the command topics
    '''
    for cmd in ('ir',):
        command_topic = f"{CONFIG.topic}{userdata['device'].id}/{cmd}/command"
        client.subscribe(command_topic, 0)
        logger.info('Subscribed to %s', command_topic)

def on_message(client, userdata, msg):
    '''
    On message received, check if the topic is a command topic
    '''
    logger.info('Received %s on %s', msg.payload, msg.topic)

    if not msg.payload:
        return

    device: Device = userdata['device']

    name = str(msg.payload)[2:-1]

    try:
        if name not in template:
            raise KeyError(f"A chave '{name}' não foi encontrada no dicionário.")
        command = template[name]
        logger.info(command)
        ir = device.tuya
        payload = ir.generate_payload(tinytuya.CONTROL, {"201": command})
        ir.send(payload)
    except Exception as e:
        logger.exception(e)

def poll(device: Device):
    '''
    Start MQTT threads.

    Params:
        device: An instance of Device dataclass
    '''
    logger.debug('Connecting to %s', device.ip)

    device.tuya = tinytuya.Device(device.id, device.ip, device.key)
    device.tuya.set_version(device.version)

    # Connect to the broker and hookup the MQTT message event handler
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=device.id, userdata={'device': device})
    client.username_pw_set(CONFIG.mqtt_user, CONFIG.mqtt_pass)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(CONFIG.host, CONFIG.port, 60)
    client.loop_forever()

template = read_template_file("template.txt")

CONFIG = read_config()

for device in read_devices():
    t = threading.Thread(target=poll, args=(device,))
    t.start()

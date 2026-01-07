import json
import logging
import subprocess
import time

import evdev
import paho.mqtt.client as mqtt
from bbev import calculate_weight_with_statistics
from paho.mqtt.enums import CallbackAPIVersion

disconnect_address = "00:23:31:75:10:A4"

BROKER = "192.168.1.186"
PORT = 1883
CONFIGTOPIC = "homeassistant/sensor/wiifitboard/config"
DATATOPIC = "stat/mqttdiscovery/sensor/wiifitboard"
CLIENT_ID = "wiifitboardscale"
USERNAME = "dmitry"
PASSWORD = "1234"

FIRST_RECONNECT_DELAY = 1
RECONNECT_RATE = 2
MAX_RECONNECT_COUNT = 12
MAX_RECONNECT_DELAY = 60

FLAG_EXIT = False


def on_connect(client, userdata, flags, rc, properties):
    if rc == 0 and client.is_connected():
        print("Connected to MQTT Broker!")
        client.subscribe(CONFIGTOPIC)
    else:
        print(f"Failed to connect, return code {rc}")


def on_disconnect(client, userdata, rc):
    logging.info("Disconnected with result code: %s", rc)
    reconnect_count, reconnect_delay = 0, FIRST_RECONNECT_DELAY
    while reconnect_count < MAX_RECONNECT_COUNT:
        logging.info("Reconnecting in %d seconds...", reconnect_delay)
        time.sleep(reconnect_delay)

        try:
            client.reconnect()
            logging.info("Reconnected successfully!")
            return
        except Exception as err:
            logging.error("%s. Reconnect failed. Retrying...", err)

        reconnect_delay *= RECONNECT_RATE
        reconnect_delay = min(reconnect_delay, MAX_RECONNECT_DELAY)
        reconnect_count += 1
    logging.info("Reconnect failed after %s attempts. Exiting...", reconnect_count)
    global FLAG_EXIT
    FLAG_EXIT = True


def on_message(client, userdata, msg):
    print(f"Received `{msg.payload.decode()}` from `{msg.topic}` topic")


def connect_mqtt():
    client = mqtt.Client(CallbackAPIVersion.VERSION2, CLIENT_ID)
    client.username_pw_set(USERNAME, PASSWORD)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(BROKER, PORT, keepalive=120)
    client.on_disconnect = on_disconnect
    return client


def get_board():
    devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
    try:
        device_path = (
            device.path
            for device in devices
            if device.name == "Nintendo Wii Remote Balance Board"
        ).__next__()
        balance_board: evdev.InputDevice = evdev.InputDevice(
            device_path,
        )
        return balance_board
    except StopIteration:
        pass

    return False


def publishdiscovery(client):
    msg_dict_discovery = {
        "dev": {
            "ids": "dmi1234",
            "name": "MQTT Wii Fit Board",
        },
        "origin": {
            "name": "dmiwiiscale",
        },
        "cmps": {
            "weight01": {
                "p": "sensor",
                "unit_of_measurement": "g",
                "value_template": "{{ value_json.mean}}",
                "unique_id": "wiiweight01",
            },
            "weight02": {
                "p": "sensor",
                "unit_of_measurement": "g",
                "value_template": "{{ value_json.median}}",
                "unique_id": "wiiweight02",
            },
        },
        "state_topic": "stat/mqttdiscovery/sensor/weightscale",
        "qos": 2,
    }

    msg = json.dumps(msg_dict_discovery)
    if not client.is_connected():
        logging.error("publish: MQTT client is not connected!")
    result = client.publish(CONFIGTOPIC, msg)
    status = result[0]
    if status == 0:
        print(f"Send `{msg}` to topic `{CONFIGTOPIC}`")
    else:
        print(f"Failed to send message to topic {CONFIGTOPIC}")


def publish(client, stats, msg_count):
    msg_dict = {
        "msgcount": msg_count,
        "median": stats["median"],
        "mean": stats["mean"],
        "stdev": stats["stdev"],
    }
    msg = json.dumps(msg_dict)
    if not client.is_connected():
        logging.error("publish: MQTT client is not connected!")
    result = client.publish(DATATOPIC, msg)
    # result: [0, 1]
    status = result[0]
    if status == 0:
        print(f"Send `{msg}` to topic `{DATATOPIC}`")
    else:
        print(f"Failed to send message to topic {DATATOPIC}")


def measure_weight():
    msg_count = 0
    while True:
        connected = False
        board = None

        client = connect_mqtt()
        client.loop_start()

        while not connected:
            print("\a Waiting for Balance board...")
            board = get_board()
            if board:
                break
        print("is board none?")
        if board is not None:
            weight_data = calculate_weight_with_statistics(
                board,
                100,
            )

            print("is weight data none?")
            if weight_data is not None:
                trimmed_stats = weight_data.trimmed_statistics(30)
                print(f"""
                Trimmed Stats: (To get rid of outliers, like getting onto the board
                    Median: {trimmed_stats["median"]}
                    Mean: {trimmed_stats["mean"]}
                    Stdev: {trimmed_stats["stdev"]}
                """)
                publishdiscovery(client)
                msg_count = msg_count + 1
                publish(client, trimmed_stats, msg_count)

            else:
                print("weight data is none")
            subprocess.run(
                ["/usr/bin/env", "bluetoothctl", "disconnect", disconnect_address],
                capture_output=True,
            )
        else:
            print("board is none")
            subprocess.run(
                ["/usr/bin/env", "bluetoothctl", "disconnect", disconnect_address],
                capture_output=True,
            )
        client.loop_stop()


if __name__ == "__main__":
    measure_weight()

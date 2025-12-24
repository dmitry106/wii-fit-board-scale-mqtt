# import json
import logging

# from systemd.journal import JournalHandler
import subprocess
import time
import traceback

import evdev
import paho.mqtt.client as mqtt
from bbev import calculate_weight_with_statistics
from ha_mqtt_discoverable import Settings
from ha_mqtt_discoverable.sensors import Sensor, SensorInfo
from paho.mqtt.enums import CallbackAPIVersion

DISCONNECT_ADDRESS = "00:23:31:75:10:A4"

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

# FLAG_EXIT = False


def on_connect(client, userdata, flags, rc, properties):
    if rc == 0 and client.is_connected():
        print("Connected to MQTT Broker!")
        client.subscribe(CONFIGTOPIC)
    else:
        print(f"Failed to connect, return code {rc}")


def on_disconnect(client, userdata, flags, reason_code, properties):
    logging.info("Disconnected with result code: %s", reason_code)
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
    # global FLAG_EXIT
    # FLAG_EXIT = True


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


def measure_weight():
    logging.basicConfig(
        format="[%(levelname)s] %(asctime)s %(message)s", level=logging.INFO
    )
    logger = logging.getLogger()

    while True:
        try:
            connected = False
            board = None

            client = connect_mqtt()
            client.loop_start()

            mqtt_settings = Settings.MQTT(client=client)

            sensor_info = SensorInfo(
                name="wiifitboard",
                device_class="weight",
                unit_of_measurement="g",
            )

            settings = Settings(mqtt=mqtt_settings, entity=sensor_info)
            mysensor = Sensor(settings)

            while not connected:
                board = get_board()
                if board:
                    logger.info("get_board() successful")
                    break
            if board is not None:
                weight_data = calculate_weight_with_statistics(
                    board,
                    100,
                )
                if weight_data is not None:
                    trimmed_stats = weight_data.trimmed_statistics(30)
                    # testing print() for before mqtt is working
                    # print(f"""
                    # Trimmed Stats: (To get rid of outliers, like getting onto the board
                    #     Median: {trimmed_stats["median"]}
                    #     Mean: {trimmed_stats["mean"]}
                    #     Stdev: {trimmed_stats["stdev"]}
                    # """)
                    logger.info("sending data to mqtt")
                    mysensor.set_state(trimmed_stats["mean"])

                else:
                    logger.warning("weight data is none, try weighing longer.")
                    print("weight data is none")
                subprocess.run(
                    ["/usr/bin/env", "bluetoothctl", "disconnect", DISCONNECT_ADDRESS],
                    capture_output=True,
                )
            else:
                logger.info("board is none, turning off board")
                subprocess.run(
                    ["/usr/bin/env", "bluetoothctl", "disconnect", DISCONNECT_ADDRESS],
                    capture_output=True,
                )
            client.loop_stop()
        except Exception as e:
            logger.error(e)
            logger.error(traceback.format_exc())


if __name__ == "__main__":
    measure_weight()

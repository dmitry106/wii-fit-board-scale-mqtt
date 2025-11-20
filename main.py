import time

import evdev
from bbev import calculate_weight_with_statistics

# devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
# device_path = (
#     device.path
#     for device in devices
#     if device.name == "Nintendo Wii Remote Balance Board"
# ).__next__()
# balance_board: evdev.InputDevice = evdev.InputDevice(
#     device_path,
# )
# weight_data = calculate_weight_with_statistics(
#     balance_board,
#     100,
# )

# stats = weight_data.statistics()
# trimmed_stats = weight_data.trimmed_statistics(30)

# print(f"""
# Stats:
#     Median: {stats["median"]}
#     Mean: {stats["mean"]}
#     Stdev: {stats["stdev"]}
# """)

# print(f"""
# Trimmed Stats: (To get rid of outliers, like getting onto the board
#     Median: {trimmed_stats["median"]}
#     Mean: {trimmed_stats["mean"]}
#     Stdev: {trimmed_stats["stdev"]}
# """)


def get_board():
    devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
    device_path = (
        device.path
        for device in devices
        if device.name == "Nintendo Wii Remote Balance Board"
    ).__next__()
    balance_board: evdev.InputDevice = evdev.InputDevice(
        device_path,
    )
    return balance_board


def measure_weight():
    while True:
        connected = False
        board = None

        while not connected:
            print("\a Waiting for Balance board...")
            board = get_board()
            if board:
                break
            time.sleep(0.5)

        if board is not None:
            weight_data = calculate_weight_with_statistics(
                board,
                100,
            )
            if weight_data is not None:
                trimmed_stats = weight_data.trimmed_statistics(30)
                print(f"""
                Trimmed Stats: (To get rid of outliers, like getting onto the board
                    Median: {trimmed_stats["median"]}
                    Mean: {trimmed_stats["mean"]}
                    Stdev: {trimmed_stats["stdev"]}
                """)
            else:
                print("weight data is none")
        else:
            print("board is none")


if __name__ == "__main__":
    measure_weight()

import evdev
from bbev import calculate_weight_with_statistics

devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
device_path = (
    device.path
    for device in devices
    if device.name == "Nintendo Wii Remote Balance Board"
).__next__()
balance_board: evdev.InputDevice = evdev.InputDevice(
    device_path,
)
weight_data = calculate_weight_with_statistics(
    balance_board,
    100,
)

stats = weight_data.statistics()
trimmed_stats = weight_data.trimmed_statistics(30)

print(f"""
Stats:
    Median: {stats["median"]}
    Mean: {stats["mean"]}
    Stdev: {stats["stdev"]}
""")

print(f"""
Trimmed Stats: (To get rid of outliers, like getting onto the board
    Median: {trimmed_stats["median"]}
    Mean: {trimmed_stats["mean"]}
    Stdev: {trimmed_stats["stdev"]}
""")

"""Entry point for the pipeline inspection rover.

Runs the control loop: fetch a command from the backend API, read the
ultrasonic sensors, then drive the motors and raise alerts accordingly.
"""

import time

from core.comms import fetch_command, send_email_alert
from core.motors import Backward, Forward, Stop, set_speed
from core.sensors import obstacle_detected

# Maps an API speed command to its duty cycle and log label.
SPEED_COMMANDS = {
    "high": (100, "HIGH"),
    "mid": (50, "MEDIUM"),
    "low": (25, "LOW"),
}

DIRECTION_COMMANDS = ("forward", "backward", "stop")

direction = "stop"
email_sent = False  # Prevent multiple alerts for the same event
event_handled = True  # True when the obstacle has been handled or cleared

latitude = 90.9828  # Dummy location
longitude = 92.2324

print("🚀 Starting Pipeline Rover Telemetry...")

while True:
    try:
        # 1. Fetch command from the API.
        command = fetch_command()
        if command:
            print(f"Command received: {command}")

            if command in SPEED_COMMANDS:
                speed, label = SPEED_COMMANDS[command]
                set_speed(speed)
                print(f"Speed set: {label}")

            elif command in DIRECTION_COMMANDS:
                if direction != command:
                    if command in ("backward", "stop"):
                        # Robot moved back or stopped, so the event is handled.
                        event_handled = True
                        print("✅ Obstacle event handled. Ready for new alert.")
                    direction = command

        # 2. Read sensors.
        obstacle = obstacle_detected()

        # 3. Execute movement and alerts.
        if direction == "forward":
            if obstacle:
                Stop()
                print("⚠️ Obstacle detected! Robot stopped automatically.")

                if not email_sent and event_handled:
                    send_email_alert(
                        "Obstacle Detected - Robot Stopped",
                        f"Obstacle detected, currently at location; lat: {latitude}, long: {longitude}, awaiting backward or stop command.",
                    )
                    email_sent = True
                    event_handled = False  # Wait until handled before alerting again
                direction = "stop"
            else:
                Forward()
                if email_sent and not obstacle:
                    email_sent = False
                    event_handled = True

        elif direction == "backward":
            Backward()
            event_handled = True

        elif direction == "stop":
            Stop()

        time.sleep(0.5)

    except Exception as e:
        print(f"❌ Error occurred: {e}")
        Stop()
        time.sleep(1)

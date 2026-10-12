# Pipeline Inspection Rover

An autonomous Raspberry Pi rover that inspects pipelines, streams telemetry back through a remote API, and emails an alert the moment it detects an obstacle it cannot clear on its own.

The rover polls a backend endpoint for drive commands, continuously samples three HC-SR04 ultrasonic sensors, and drives a single DC motor through an L298N-style H-bridge. When an obstacle appears inside the safety threshold while advancing, the rover stops itself, records its location, and notifies a technician by email so a human can decide whether to reverse, hold, or intervene.

---

## Table of Contents

- [Features](#features)
- [How It Works](#how-it-works)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Hardware Requirements](#hardware-requirements)
- [GPIO Pin Map](#gpio-pin-map)
- [Software Requirements](#software-requirements)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Backend API Contract](#backend-api-contract)
- [Tuning and Constants](#tuning-and-constants)
- [Troubleshooting](#troubleshooting)
- [Design Notes and Limitations](#design-notes-and-limitations)
- [License](#license)

---

## Features

- **Remote command control** — Speed (`low` / `mid` / `high`) and direction (`forward` / `backward` / `stop`) are driven entirely by the backend API, so no code change is needed to change rover behaviour.
- **Triple-sensor obstacle detection** — Three HC-SR04 sensors give left, centre, and right coverage; the rover stops if *any* sensor reports an object within the threshold.
- **Fail-safe stop on fault** — Any unhandled exception in the control loop triggers an immediate motor stop before the loop retries.
- **Deduplicated email alerting** — An alert is sent once per obstacle event. It is only re-armed after the rover has been driven backward or stopped, preventing alert storms.
- **Echo timeout handling** — Sensors that never return an echo (no object in range, or wiring fault) are logged as `n/a` instead of blocking the loop.
- **Live telemetry logging** — Every cycle prints the current command, speed, and all three distance readings to the console.

---

## How It Works

`main.py` runs a single `while True` control loop. Each iteration performs four steps:

1. **Fetch a command** from the backend API (`GET API_COMMAND_URL`). The response body's `command` field is applied if present.
2. **Apply the command.** Speed commands change the PWM duty cycle; direction commands update the rover's intended direction.
3. **Read the sensors.** All three ultrasonic sensors are sampled and their distances logged.
4. **Act.** Movement and alerting are executed according to the direction and sensor state.

### Obstacle state machine

The rover tracks two flags to avoid repeat alerts:

| Flag | Meaning |
| --- | --- |
| `email_sent` | An alert has already been sent for the current obstacle event. |
| `event_handled` | The obstacle event has been dealt with (rover was reversed or stopped). |

Sequence of a typical event:

```
forward + clear path   -> Forward(), alert re-armed
forward + obstacle      -> Stop(), email sent once, direction forced to "stop"
backward or stop command-> event_handled = True, alert re-armed
```

While advancing, the rover asserts that the path is clear, which resets `email_sent` so the *next* genuine obstacle raises a fresh alert.

---

## Architecture

```
                +---------------------------+
                |   Backend API (command)   |
                +-------------+-------------+
                              |  GET /command
                              v
   +--------------------------------------------------+
   |                     main.py                      |
   |  fetch -> decide -> sense -> drive -> alert      |
   +------+------------------------------+------------+
          |                              |
          v                              v
   +--------------+              +----------------+
   | core/sensors |              |  core/motors   |
   |  HC-SR04 x3  |              |  H-bridge PWM  |
   +--------------+              +----------------+
          |                              |
          v                              v
     GPIO 2/3,                    GPIO 23/24/25
    27/22, 16/26                     (BCM)
                              +----------------+
                              |  core/comms    |
                              | Gmail SMTP     |
                              +----------------+
```

---

## Project Structure

```
pipeline-inspection-rover/
├── main.py             # Entry point: the control loop
├── requirements.txt    # Python dependencies
├── .env.example        # Template for required secrets and endpoints
├── .gitignore          # Excludes .env and Python bytecode
└── core/
    ├── __init__.py     # Package docstring / module map
    ├── config.py       # Loads .env secrets and the API endpoint
    ├── motors.py       # GPIO setup, PWM speed control, movement primitives
    ├── sensors.py      # HC-SR04 ultrasonic ranging and obstacle detection
    └── comms.py        # Gmail SMTP alerting and backend API requests
```

---

## Hardware Requirements

| Component | Notes |
| --- | --- |
| Raspberry Pi | Any model with 40-pin GPIO and `RPi.GPIO` support (3 / 4 / Zero). |
| HC-SR04 ultrasonic sensors × 3 | One per facing (left / centre / right). Operate at 5 V and need level-shifted echo lines on a 3.3 V Pi. |
| DC motor + motor driver | H-bridge driver exposing an enable/PWM pin and two direction pins (L298N or equivalent). |
| Chassis and power supply | Must supply the motor rail independently of the Pi's 5 V rail to avoid brown-outs. |

> **Level shifting:** HC-SR04 echo pins output 5 V. Use a voltage divider or level shifter on each echo line to protect the Pi's 3.3 V GPIO.
>
> **Common ground:** The motor driver, the sensors, and the Pi must share a ground.

---

## GPIO Pin Map

All pins use BCM numbering.

### Motors — `core/motors.py`

| Signal | BCM Pin | Direction | Purpose |
| --- | --- | --- | --- |
| `IN1` | 24 | Output | Direction pin A |
| `IN2` | 23 | Output | Direction pin B |
| `EN1` | 25 | Output / PWM | Motor enable (PWM at 100 Hz) |

| Parameter | Value |
| --- | --- |
| PWM frequency | 100 Hz |
| Duty cycle at import | 25 % |
| Default run duty (`SPEED`) | 50 % |
| Forward | `IN1 = HIGH`, `IN2 = LOW` |
| Backward | `IN1 = LOW`, `IN2 = HIGH` |
| Stop | `IN1 = LOW`, `IN2 = LOW` |

### Sensors — `core/sensors.py`

| Sensor | TRIG (BCM) | ECHO (BCM) |
| --- | --- | --- |
| 1 | 2 | 3 |
| 2 | 27 | 22 |
| 3 | 16 | 26 |

---

## Software Requirements

- **Python** 3.8 or newer.
- **Raspberry Pi OS** (or any Linux distribution on a Pi) with GPIO access.
- Runtime dependencies:

  | Package | Purpose |
  | --- | --- |
  | `python-dotenv` | Loads secrets from the local `.env` file. |
  | `requests` | Calls the backend command endpoint. |
  | `RPi.GPIO` | GPIO and PWM access (pre-installed on Raspberry Pi OS; see the note below). |

---

## Installation

1. **Clone the repository onto the Pi.**

   ```bash
   git clone https://github.com/Muheezabiola/pipeline-inspection-rover.git
   cd pipeline-inspection-rover
   ```

2. **Create and activate a virtual environment** (recommended).

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install the dependencies.**

   ```bash
   pip install -r requirements.txt
   ```

   > `RPi.GPIO` is intentionally not listed in `requirements.txt` because it ships with Raspberry Pi OS and does not build on non-Pi hardware. If your image is missing it, install it with `pip install RPi.GPIO` (or `sudo apt install python3-rpi.gpio`).

4. **Create your environment file.**

   ```bash
   cp .env.example .env
   ```

   Then fill in the values described in [Configuration](#configuration).

---

## Configuration

All configuration is read from environment variables (loaded from `.env` by `core/config.py`) so no secrets live in the source tree.

| Variable | Required | Description |
| --- | --- | --- |
| `GMAIL_USER` | Yes | Gmail address the alert is sent *from*. |
| `GMAIL_APP_PASSWORD` | Yes | 16-character Gmail [App Password](https://support.google.com/accounts/answer/185833) — not your account password. |
| `TARGET_EMAIL` | Yes | Recipient of obstacle alerts. |
| `API_COMMAND_URL` | Yes | Full URL returning the current drive command as JSON. |

`.env` is listed in `.gitignore` and must never be committed.

> **Gmail app passwords** require 2-Step Verification to be enabled on the account. Standard account passwords are rejected by SMTP.

---

## Usage

Run the control loop from the project root:

```bash
python main.py
```

Expected startup and steady-state output:

```
🚀 Starting Pipeline Rover Telemetry...
Command received: forward
➡️ Moving forward...
Distances: 145.2 cm, 88.6 cm, n/a
Distances: 132.0 cm, 74.1 cm, n/a
⚠️ Obstacle detected! Robot stopped automatically.
⏹️ Stopped.
✅ Email alert sent successfully.
```

Stop the rover with `Ctrl+C`.

To run it unattended (for example on boot), a systemd service or `cron` `@reboot` entry can invoke `python main.py` from the project directory once the virtual environment is active.

---

## Backend API Contract

`core/comms.py` performs a single unauthenticated `GET` request per loop iteration and expects a JSON body with a `command` field:

```json
{ "command": "forward" }
```

| Command | Effect |
| --- | --- |
| `high` | Sets motor duty cycle to 100 %. |
| `mid` | Sets motor duty cycle to 50 %. |
| `low` | Sets motor duty cycle to 25 %. |
| `forward` | Drives forward; obstacle checking is active. |
| `backward` | Drives backward; re-arms the obstacle alert. |
| `stop` | Stops the rover; re-arms the obstacle alert. |

Behaviour notes:

- Any non-`200` response is treated as "no command" and the loop continues with the previous state.
- Unknown or unrecognised command strings are ignored.
- The endpoint is polled roughly twice per second (see the `time.sleep(0.5)` in the loop).
- The request is unauthenticated — put the endpoint behind a trusted network, a VPN, or add a token header before exposing it publicly.

---

## Tuning and Constants

| Constant | File | Default | Effect |
| --- | --- | --- | --- |
| `OBSTACLE_THRESHOLD_CM` | [core/sensors.py](core/sensors.py) | `20` | Stop distance for obstacle detection. |
| `ECHO_TIMEOUT_S` | [core/sensors.py](core/sensors.py) | `0.03` | Max wait for an echo (~4 m round trip); prevents blocking when no object is in range. |
| `SPEED` | [core/motors.py](core/motors.py) | `50` | Default duty cycle applied on movement. |
| `SPEED_COMMANDS` | [main.py](main.py) | `high`/`mid`/`low` | Maps command strings to duty cycles and log labels. |
| `latitude` / `longitude` | [main.py](main.py) | dummy values | Location stamped into alert emails — replace with a real GPS/GNSS source. |
| Loop delay | [main.py](main.py) | `0.5` s | API poll and sensor sample interval. |

Distance is computed as `pulse_duration × 17150` cm, derived from the speed of sound with the round-trip factor already applied.

---

## Troubleshooting

| Symptom | Likely cause and fix |
| --- | --- |
| `ModuleNotFoundError: No module named 'RPi.GPIO'` | You are not on a Raspberry Pi, or the module is missing. Install it on the Pi with `pip install RPi.GPIO`. |
| `RuntimeError: No access to /dev/mem` | Run with sufficient privileges (`sudo python main.py`) or add your user to the `gpio` group. |
| Motor never turns | Check that `EN1` is wired to the driver's enable pin and that the motor supply rail has power; the PWM duty cycle must be above 0. |
| `❌ Failed to send email` | Verify `GMAIL_APP_PASSWORD` is an App Password (not the account password) and that 2-Step Verification is enabled. |
| Alerts repeat too often | Confirm the rover is issuing `backward` or `stop` after an obstacle so `event_handled` is set. |
| Distances always `n/a` | Echo pin is not wired or not level-shifted, or the sensor has no 5 V supply. |
| Erratic distance readings | Cross-talk between HC-SR04 sensors — trigger them sequentially (as the current code does) and keep sensors angled apart. |

---

## Design Notes and Limitations

- **Single motor channel.** The current driver exposes one motor (direction + PWM). A real differential-drive chassis needs a second channel for turning.
- **One-way API.** Commands flow from the backend to the rover; sensor telemetry is only logged locally and is not yet pushed back upstream.
- **Dummy localisation.** `latitude` and `longitude` are hard-coded placeholders in `main.py`.
- **Unauthenticated transport.** Both SMTP credentials and the API are plain environment values — no secrets manager, no request signing.
- **Fail-safe behaviour.** The exception handler stops the motors before retrying, so a transient sensor or network error results in a stationary rover rather than an unmonitored one.

---

## License

Released under the [MIT License](LICENSE) © 2026 Muiz Abiola Aminu.

You are free to use, copy, modify, merge, publish, distribute, sublicense, and sell copies of this software, provided the copyright notice and permission notice are retained.

"""Ultrasonic distance sensing for obstacle detection."""

import time

import RPi.GPIO as GPIO

# HC-SR04 sensor pins (BCM numbering).
TRIG1, ECHO1 = 2, 3
TRIG2, ECHO2 = 27, 22
TRIG3, ECHO3 = 16, 26

GPIO.setmode(GPIO.BCM)
for _trig, _echo in ((TRIG1, ECHO1), (TRIG2, ECHO2), (TRIG3, ECHO3)):
    GPIO.setup(_trig, GPIO.OUT)
    GPIO.setup(_echo, GPIO.IN)
    GPIO.output(_trig, False)

OBSTACLE_THRESHOLD_CM = 20

# ~4 m round trip for an HC-SR04; also covers the common "no object in range"
# case, where the echo pin never goes high.
ECHO_TIMEOUT_S = 0.03


def _format(distance):
    """Format a reading for logging, showing 'n/a' when no echo was received."""
    return "n/a" if distance is None else f"{distance} cm"


def get_distance(trig, echo):
    """Return the distance in centimetres, or None if no echo is received."""
    GPIO.output(trig, True)
    time.sleep(0.00001)
    GPIO.output(trig, False)

    deadline = time.time() + ECHO_TIMEOUT_S

    # Wait for the echo pulse to start.
    pulse_start = time.time()
    while GPIO.input(echo) == 0:
        pulse_start = time.time()
        if pulse_start > deadline:
            return None

    # Wait for the echo pulse to end.
    pulse_end = time.time()
    while GPIO.input(echo) == 1:
        pulse_end = time.time()
        if pulse_end > deadline:
            return None

    pulse_duration = pulse_end - pulse_start
    return round(pulse_duration * 17150, 2)


def obstacle_detected():
    """Return True when any sensor reports an obstacle within the threshold."""
    readings = (
        get_distance(TRIG1, ECHO1),
        get_distance(TRIG2, ECHO2),
        get_distance(TRIG3, ECHO3),
    )
    print("Distances: " + ", ".join(_format(r) for r in readings))

    if None in readings:
        print(f"⚠️ {readings.count(None)} sensor(s) returned no echo.")

    return any(
        distance is not None and distance < OBSTACLE_THRESHOLD_CM
        for distance in readings
    )

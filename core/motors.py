"""Motor driver setup and movement primitives for the rover."""

import RPi.GPIO as GPIO

# Motor driver pins (BCM numbering).
IN1, IN2, EN1 = 24, 23, 25

GPIO.setmode(GPIO.BCM)
for _pin in (IN1, IN2, EN1):
    GPIO.setup(_pin, GPIO.OUT)
    GPIO.output(_pin, GPIO.LOW)

_pwm = GPIO.PWM(EN1, 100)
_pwm.start(25)

SPEED = 50


def set_speed(speed):
    """Set the motor duty cycle to ``speed`` (0-100)."""
    global SPEED
    SPEED = speed
    _pwm.ChangeDutyCycle(SPEED)


def Forward():
    GPIO.output(IN1, GPIO.HIGH)
    GPIO.output(IN2, GPIO.LOW)
    _pwm.ChangeDutyCycle(SPEED)
    print("➡️ Moving forward...")


def Backward():
    GPIO.output(IN1, GPIO.LOW)
    GPIO.output(IN2, GPIO.HIGH)
    _pwm.ChangeDutyCycle(SPEED)
    print("⬅️ Moving backward...")


def Stop():
    GPIO.output(IN1, GPIO.LOW)
    GPIO.output(IN2, GPIO.LOW)
    print("⏹️ Stopped.")

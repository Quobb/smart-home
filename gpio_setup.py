import RPi.GPIO as GPIO
from config import *
from actuators import servo_pwm_init

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

# Actuators
GPIO.setup(PIN_SERVO, GPIO.OUT)
GPIO.setup(PIN_LIGHT, GPIO.OUT, initial=GPIO.LOW)
GPIO.setup(PIN_BUZZER, GPIO.OUT, initial=GPIO.LOW)
GPIO.setup(PIN_BUZZER2, GPIO.OUT, initial=GPIO.LOW)

# PIR
GPIO.setup(PIN_PIR1, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(PIN_PIR2, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

# Initialize servo PWM
servo_pwm = servo_pwm_init(PIN_SERVO)

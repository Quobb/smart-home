from gpiozero import Servo, LED, Buzzer
from time import sleep
from config import PIN_SERVO, PIN_LIGHT, PIN_BUZZER,PIN_BUZZER_2, SERVO_OPEN_DC, SERVO_CLOSED_DC
from utils import log_event

# Servo setup
servo = Servo(PIN_SERVO)
light = LED(PIN_LIGHT)
buzzer = Buzzer(PIN_BUZZER)
buzzer_2 = Buzzer(PIN_BUZZER_2)

def servo_open():
    log_event("Opening gate")
    servo.value = SERVO_OPEN_DC  # approximate open position
    sleep(1)
    servo.value = None

def servo_close():
    log_event("Closing gate")
    servo.value = SERVO_CLOSED_DC  # approximate closed position
    sleep(1)
    servo.value = None

def light_on():
    light.on()
    log_event("Light ON")

def light_off():
    light.off()
    log_event("Light OFF")

def buzzer_on():
    buzzer.on()
    buzzer_2.on()
    log_event("Buzzer ON")

def buzzer_off():
    buzzer.off()
    buzzer_2.off()
    log_event("Buzzer OFF")

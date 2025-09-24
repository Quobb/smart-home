#!/usr/bin/env python3
"""
smart_home_pi.py
Raspberry Pi Smart Home + Intrusion Detection (Updated Pinout)

Features:
- RFID (MFRC522) for access control
- Servo motor (gate)
- PIR motion sensors
- DHT22 temperature & humidity
- MQ-series smoke/gas via MCP3008 ADC
- DC bulb for lights
- Buzzer alarm
- Camera capture (OpenCV)
- GSM (SIM800L) SMS alerts via UART (AT commands)
"""
import time
import threading
import os
import sys
from datetime import datetime

import RPi.GPIO as GPIO
from gpiozero import MCP3008
import serial
import cv2
import Adafruit_DHT

# RFID
try:
    from pirc522 import RFID
    RFID_AVAILABLE = True
except Exception:
    print("pirc522 not available - RFID functionality disabled.")
    RFID_AVAILABLE = False

# ----------------------------
# === PIN CONFIGURATION ======
# ----------------------------
PIN_SERVO   = 16     # Servo motor, GPIO16, Pin 36
PIN_PIR1    = 23     # PIR sensor 1, GPIO23, Pin 16
PIN_PIR2    = 24     # PIR sensor 2, GPIO24, Pin 18
PIN_LIGHT   = 27     # DC bulb, GPIO27, Pin 13
PIN_BUZZER  = 25     # Buzzer, GPIO25
PIN_BUZZER2 = 26     # Optional 2nd buzzer, GPIO26
DHT_PIN     = 4      # Humidity/Temp, GPIO4, Pin 7
DHT_SENSOR  = Adafruit_DHT.DHT22
RFID_IRQ    = 26     # GPIO26, Pin 37

# MCP3008 channel for MQ sensor
MQ_CHANNEL = 0

# GSM
GSM_SERIAL_PORT = "/dev/serial0"
GSM_BAUDRATE = 9600

# Servo PWM duty cycles
SERVO_OPEN_DC   = 7.5
SERVO_CLOSED_DC = 12.5

# Camera
CAMERA_INDEX = 0

# Thresholds
SMOKE_THRESHOLD = 0.35
MOTION_ARM_HOUR_START = 22
MOTION_ARM_HOUR_END   = 6

# SMS recipients
ALERT_PHONE_NUMBERS = ["+1234567890"]

# Logging
LOG_DIR = "/home/malware/smart_home_logs"
os.makedirs(LOG_DIR, exist_ok=True)

# ----------------------------
# === GPIO SETUP ============
# ----------------------------
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

# Actuators
GPIO.setup(PIN_SERVO, GPIO.OUT)
GPIO.setup(PIN_LIGHT, GPIO.OUT, initial=GPIO.LOW)
GPIO.setup(PIN_BUZZER, GPIO.OUT, initial=GPIO.LOW)
GPIO.setup(PIN_BUZZER2, GPIO.OUT, initial=GPIO.LOW)

# PIR sensors
GPIO.setup(PIN_PIR1, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(PIN_PIR2, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

# Servo PWM
servo_pwm = GPIO.PWM(PIN_SERVO, 50)
servo_pwm.start(SERVO_CLOSED_DC)

# MCP3008 MQ sensor
mq_sensor = MCP3008(channel=MQ_CHANNEL)

# RFID
rfid = None
if RFID_AVAILABLE:
    try:
        rfid = RFID(pin_mode=GPIO.BCM, pin_irq=RFID_IRQ)
    except Exception as e:
        print("Warning: RFID init failed:", e)
        rfid = None
        RFID_AVAILABLE = False

# GSM Serial
gsm_serial = None
def open_gsm():
    global gsm_serial
    if gsm_serial and gsm_serial.is_open:
        return gsm_serial
    try:
        gsm_serial = serial.Serial(GSM_SERIAL_PORT, GSM_BAUDRATE, timeout=1)
        time.sleep(0.5)
        return gsm_serial
    except Exception as e:
        print("Failed to open GSM serial:", e)
        gsm_serial = None
        return None

# ----------------------------
# === UTILITIES =============
# ----------------------------
def log_event(msg):
    ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    line = f"{ts} UTC | {msg}"
    print(line)
    with open(os.path.join(LOG_DIR, "events.log"), "a") as f:
        f.write(line + "\n")

def send_sms(text, recipients=ALERT_PHONE_NUMBERS):
    ser = open_gsm()
    if not ser:
        log_event("GSM unavailable: SMS not sent.")
        return False
    for number in recipients:
        try:
            log_event(f"Sending SMS to {number}: {text}")
            ser.write(b'AT\r')
            time.sleep(0.5)
            ser.write(b'AT+CMGF=1\r')
            time.sleep(0.5)
            cmd = f'AT+CMGS="{number}"\r'.encode()
            ser.write(cmd)
            time.sleep(0.5)
            ser.write(text.encode() + b"\r")
            time.sleep(0.5)
            ser.write(bytes([26]))
            time.sleep(3)
            log_event("SMS send sequence finished.")
        except Exception as e:
            log_event(f"Error sending SMS to {number}: {e}")
    return True

def capture_image(prefix="intruder"):
    ts = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    filename = os.path.join(LOG_DIR, f"{prefix}_{ts}.jpg")
    try:
        cap = cv2.VideoCapture(CAMERA_INDEX)
        time.sleep(0.5)
        ret, frame = cap.read()
        cap.release()
        if ret:
            cv2.imwrite(filename, frame)
            log_event(f"Image captured: {filename}")
            return filename
        else:
            log_event("Camera capture failed")
            return None
    except Exception as e:
        log_event(f"Camera error: {e}")
        return None

# ----------------------------
# === ACTUATORS =============
# ----------------------------
def servo_open():
    log_event("Opening servo/gate")
    servo_pwm.ChangeDutyCycle(SERVO_OPEN_DC)
    time.sleep(1)
    servo_pwm.ChangeDutyCycle(0)
    log_event("Gate opened")

def servo_close():
    log_event("Closing servo/gate")
    servo_pwm.ChangeDutyCycle(SERVO_CLOSED_DC)
    time.sleep(1)
    servo_pwm.ChangeDutyCycle(0)
    log_event("Gate closed")

def light_on():
    GPIO.output(PIN_LIGHT, GPIO.HIGH)
    log_event("Light ON")

def light_off():
    GPIO.output(PIN_LIGHT, GPIO.LOW)
    log_event("Light OFF")

def buzzer_on():
    GPIO.output(PIN_BUZZER, GPIO.HIGH)
    log_event("Buzzer ON")

def buzzer_off():
    GPIO.output(PIN_BUZZER, GPIO.LOW)
    log_event("Buzzer OFF")

# ----------------------------
# === SENSOR READERS =========
# ----------------------------
def read_dht():
    try:
        humidity, temperature = Adafruit_DHT.read_retry(DHT_SENSOR, DHT_PIN)
        return (temperature, humidity)
    except Exception as e:
        log_event(f"DHT read error: {e}")
        return (None, None)

def read_smoke_level():
    try:
        return mq_sensor.value
    except Exception as e:
        log_event(f"MQ sensor error: {e}")
        return None

# ----------------------------
# === PIR HANDLER ============
# ----------------------------
def is_night_time():
    h = datetime.now().hour
    return h >= MOTION_ARM_HOUR_START or h < MOTION_ARM_HOUR_END

def motion_callback(channel):
    log_event(f"PIR sensor triggered on GPIO{channel}")
    if is_night_time():
        light_on()
        buzzer_on()
        capture_image(prefix="motion_intruder")
        send_sms("Motion detected at home!")
        time.sleep(5)
        buzzer_off()
    else:
        log_event("Motion detected outside armed hours")
        light_on()
        time.sleep(10)
        light_off()

# Attach PIR callbacks
GPIO.add_event_detect(PIN_PIR1, GPIO.RISING, callback=motion_callback, bouncetime=300)
GPIO.add_event_detect(PIN_PIR2, GPIO.RISING, callback=motion_callback, bouncetime=300)

# ----------------------------
# === MAIN LOOP =============
# ----------------------------
def main():
    log_event("Smart Home Pi starting up")
    try:
        while True:
            cmd = input("\nEnter command (help for list): ").strip()
            if cmd in ("q", "quit", "exit"):
                break
            elif cmd == "help":
                print("Commands: help, status, open, close, light_on, light_off, buzz_on, buzz_off, snap, sms_test")
            elif cmd == "status":
                temp, hum = read_dht()
                smoke = read_smoke_level()
                print(f"Temp: {temp}C Humidity: {hum}% Smoke: {smoke}")
            elif cmd == "open":
                servo_open()
            elif cmd == "close":
                servo_close()
            elif cmd == "light_on":
                light_on()
            elif cmd == "light_off":
                light_off()
            elif cmd == "buzz_on":
                buzzer_on()
            elif cmd == "buzz_off":
                buzzer_off()
            elif cmd == "snap":
                capture_image(prefix="manual_snap")
            elif cmd == "sms_test":
                send_sms("Test alert from Raspberry Pi")
            else:
                print("Unknown command")
    except KeyboardInterrupt:
        log_event("Interrupted by user")
    finally:
        log_event("Cleaning up GPIO")
        servo_pwm.stop()
        GPIO.cleanup()
        if gsm_serial and gsm_serial.is_open:
            gsm_serial.close()
        log_event("Shutdown complete")

if __name__ == "__main__":
    main()
 
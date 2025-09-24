import serial
import time
from config import ALERT_PHONE_NUMBERS, GSM_BAUDRATE, GSM_SERIAL_PORT
from utils import log_event

gsm_serial = None

def open_gsm():
    global gsm_serial
    if gsm_serial and gsm_serial.is_open:
        return gsm_serial
    try:
        gsm_serial = serial.Serial(GSM_SERIAL_PORT, GSM_BAUDRATE, timeout=1)
        time.sleep(0.5)
        log_event("GSM opened")
        return gsm_serial
    except Exception as e:
        log_event(f"GSM open error: {e}")
        gsm_serial = None
        return None

def send_sms(text, recipients=ALERT_PHONE_NUMBERS):
    ser = open_gsm()
    if not ser:
        log_event("SMS not sent, GSM unavailable")
        return False
    for number in recipients:
        try:
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
            log_event(f"SMS sent to {number}")
        except Exception as e:
            log_event(f"SMS error {number}: {e}")

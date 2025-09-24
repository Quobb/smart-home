from pirc522 import RFID
from config import PIN_RFID_IRQ
from actuators import servo_open, servo_close
from camera_module import capture_image
from utils import log_event

RFID_WHITELIST = {}

try:
    rfid_reader = RFID(pin_irq=PIN_RFID_IRQ)
except Exception as e:
    log_event(f"RFID init failed: {e}")
    rfid_reader = None

def handle_rfid():
    if not rfid_reader:
        log_event("RFID unavailable")
        return
    while True:
        rfid_reader.wait_for_tag()
        error, data = rfid_reader.request()
        if not error:
            error, uid = rfid_reader.anticoll()
            if not error:
                uid_str = ":".join(map(str, uid))
                name = RFID_WHITELIST.get(uid_str)
                if name:
                    log_event(f"RFID Authorized: {name}")
                    servo_open()
                    from time import sleep; sleep(3)
                    servo_close()
                else:
                    log_event(f"RFID Unauthorized: {uid_str}")
                    capture_image("rfid_unauth")

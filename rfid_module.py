from time import sleep
from actuators import servo_open, servo_close
from camera_module import capture_image
from utils import log_event
from mfrc522 import SimpleMFRC522

# Store UIDs as strings for consistency
RFID_WHITELIST = {}

try:
    rfid_reader = SimpleMFRC522()
except Exception as e:
    log_event(f"RFID init failed: {e}")
    rfid_reader = None


def normalize_uid(uid):
    """Convert UID (int) to string for storage/lookup."""
    return str(uid)


def handle_rfid():
    if not rfid_reader:
        log_event("RFID unavailable")
        return

    log_event("RFID reader ready...")

    while True:
        try:
            # Blocking read until card is detected
            card_id, _ = rfid_reader.read()
            uid_str = normalize_uid(card_id)

            name = RFID_WHITELIST.get(uid_str)
            if name:
                log_event(f"RFID Authorized: {name}")
                servo_open()
                sleep(3)
                servo_close()
            else:
                log_event(f"RFID Unauthorized: {uid_str}")
                capture_image("rfid_unauth")

            sleep(1)  # avoid hammering the reader
        except Exception as e:
            log_event(f"RFID read error: {e}")
            sleep(1)

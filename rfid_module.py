from mfrc522 import SimpleMFRC522
from utils import log_event
import time
from threading import Timer

# Import from main to avoid circular import
import main

rfid_reader = SimpleMFRC522()
RFID_WHITELIST = {}

def normalize_uid(uid):
    """Convert UID to consistent string format"""
    return str(uid).strip()

def handle_rfid():
    """Monitor RFID reader for card scans"""
    log_event("RFID monitoring started")
    
    while True:
        try:
            log_event("Waiting for RFID card...")
            card_id, text = rfid_reader.read()  # This blocks until card is detected
            uid_str = normalize_uid(card_id)
            
            if uid_str in RFID_WHITELIST:
                user_name = RFID_WHITELIST[uid_str]
                log_event(f"✅ Authorized RFID: {user_name} ({uid_str})")
                
                # Set authorized user status
                main.set_authorized_user(user_name)
                
                # Auto-logout after 8 hours (28800 seconds)
                def auto_logout():
                    main.clear_authorized_user()
                    log_event(f"Auto-logout: {user_name} session expired")
                
                Timer(28800, auto_logout).start()
                
            else:
                log_event(f"❌ Unauthorized RFID: {uid_str}")
                # Still trigger security measures for unknown cards
                from actuators import buzzer_on, buzzer_off
                from camera_module import capture_image
                from gsm_module import send_sms, send_image_mms
                
                buzzer_on()
                image_path = capture_image("unauthorized_rfid")
                send_sms(f"SECURITY ALERT: Unauthorized RFID card detected at {time.strftime('%Y-%m-%d %H:%M:%S')}")
                if image_path:
                    send_image_mms(image_path, "Unauthorized RFID attempt")
                
                Timer(5, buzzer_off).start()
            
            time.sleep(2)  # Prevent rapid re-reads
            
        except Exception as e:
            log_event(f"RFID error: {e}")
            time.sleep(1)

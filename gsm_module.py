import serial
import time
import base64
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
    """Send SMS to specified recipients"""
    ser = open_gsm()
    if not ser:
        log_event("SMS not sent, GSM unavailable")
        return False
    
    success_count = 0
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
            ser.write(bytes([26]))  # Ctrl+Z to send
            time.sleep(3)
            log_event(f"SMS sent to {number}")
            success_count += 1
        except Exception as e:
            log_event(f"SMS error {number}: {e}")
    
    return success_count > 0

def send_image_mms(image_path, message="Security Alert", recipients=ALERT_PHONE_NUMBERS):
    """Send image via MMS (if supported by GSM module)"""
    ser = open_gsm()
    if not ser:
        log_event("MMS not sent, GSM unavailable")
        return False
    
    try:
        # Read and encode image
        with open(image_path, 'rb') as img_file:
            img_data = base64.b64encode(img_file.read()).decode('utf-8')
        
        success_count = 0
        for number in recipients:
            try:
                # Basic MMS AT commands (varies by GSM module)
                ser.write(b'AT+CMGF=1\r')
                time.sleep(0.5)
                
                # Set MMS parameters
                ser.write(b'AT+CMMSCURL="http://mms.provider.com"\r')
                time.sleep(0.5)
                
                # Create MMS
                cmd = f'AT+CMMSSEND="{number}","{message}","image/jpeg"\r'.encode()
                ser.write(cmd)
                time.sleep(1)
                
                # Send image data (simplified - actual implementation varies)
                ser.write(img_data[:1000].encode())  # Send first 1KB as example
                ser.write(bytes([26]))  # Ctrl+Z
                time.sleep(5)
                
                log_event(f"MMS sent to {number}")
                success_count += 1
                
            except Exception as e:
                log_event(f"MMS error {number}: {e}")
                
        return success_count > 0
        
    except Exception as e:
        log_event(f"MMS preparation error: {e}")
        return False

def send_live_feed_notification(recipients=ALERT_PHONE_NUMBERS):
    """Send notification about live camera feed availability"""
    from camera_module import capture_image
    
    # Capture current image
    image_path = capture_image("live_feed")
    if image_path:
        message = f"Live camera feed at {time.strftime('%Y-%m-%d %H:%M:%S')}"
        send_image_mms(image_path, message, recipients)
        send_sms(f"Live camera feed updated: {message}", recipients)
    else:
        send_sms("Live camera feed requested but capture failed", recipients)
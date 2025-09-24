import cv2
import numpy as np
from datetime import datetime
from config import CAMERA_INDEX, BRIGHTNESS_THRESHOLD
from utils import log_event

def capture_image(prefix="intruder"):
    ts = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    filename = f"/home/malware/smart_home_logs/{prefix}_{ts}.jpg"
    cap = cv2.VideoCapture(CAMERA_INDEX)
    ret, frame = cap.read()
    cap.release()
    if ret:
        cv2.imwrite(filename, frame)
        log_event(f"Captured image: {filename}")
        return filename
    return None

def is_dark():
    cap = cv2.VideoCapture(CAMERA_INDEX)
    ret, frame = cap.read()
    cap.release()
    if not ret:
        return False
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    avg_brightness = np.mean(gray)
    log_event(f"Room brightness: {avg_brightness:.1f}")
    return avg_brightness < BRIGHTNESS_THRESHOLD

def get_frame():
    cap = cv2.VideoCapture(CAMERA_INDEX)
    ret, frame = cap.read()
    cap.release()
    if not ret:
        return None
    ret, jpeg = cv2.imencode(".jpg", frame)
    return jpeg.tobytes() if ret else None

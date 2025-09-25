import os
from datetime import datetime
import numpy as np
from picamera2 import Picamera2, Preview
from config import BRIGHTNESS_THRESHOLD
from utils import log_event

# Global camera instance
camera = None

def init_camera():
    """Initialize the Raspberry Pi camera."""
    global camera
    if camera is None:
        camera = Picamera2()
        camera.start_preview(Preview.QTGL)  # Optional, can remove if no GUI
        camera.start()
        log_event("Camera initialized successfully.")

# Call once at startup
init_camera()

def capture_image(prefix="intruder"):
    """Capture an image and save it to the logs folder."""
    global camera
    ts = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    filename = f"/home/malware/smart_home_logs/{prefix}_{ts}.jpg"

    frame = camera.capture_array()
    if frame is not None:
        from PIL import Image
        img = Image.fromarray(frame)
        img.save(filename)
        log_event(f"Captured image: {filename}")
        return filename
    else:
        log_event("Camera capture failed")
        return None

def is_dark():
    """Check if the room is dark based on the average brightness."""
    global camera
    frame = camera.capture_array()
    if frame is None:
        log_event("Camera frame grab failed")
        return False
    gray = np.mean(frame, axis=2)  # convert to grayscale by averaging channels
    avg_brightness = np.mean(gray)
    log_event(f"Room brightness: {avg_brightness:.1f}")
    return avg_brightness < BRIGHTNESS_THRESHOLD

def get_frame():
    """Return the current frame as JPEG bytes."""
    global camera
    frame = camera.capture_array()
    if frame is None:
        log_event("Camera frame grab failed")
        return None
    import cv2
    ret, jpeg = cv2.imencode(".jpg", frame)
    return jpeg.tobytes() if ret else None


get_frame()
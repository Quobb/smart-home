from gpiozero import MotionSensor, DigitalInputDevice
from threading import Thread, Timer
from actuators import light_on, light_off, buzzer_on, buzzer_off
from camera_module import capture_image, is_dark
from gsm_module import send_sms, send_image_mms
import Adafruit_DHT
from time import sleep, time
from utils import log_event
import main  # Import to check authorized user status

# === Motion Sensors ===
pir1 = MotionSensor(23)
pir2 = MotionSensor(24)

def motion_worker():
    log_event("Motion detected")
    
    # Check if authorized user is present
    if main.is_authorized_user_present():
        user_name = main.get_authorized_user_name()
        log_event(f"Motion from authorized user: {user_name}")
        
        # Only turn on light if dark, NO buzzer for authorized users
        if is_dark():
            light_on()
            log_event("Light turned on for authorized user in dark room")
            
            # Send camera feed to show room status
            image_path = capture_image("authorized_motion")
            if image_path:
                send_image_mms(image_path, f"Room activity - {user_name}")
        
        # Turn off light after 5 minutes for authorized users
        def reset_light():
            light_off()
            log_event("Light turned off after authorized user activity")
        
        Timer(300, reset_light).start()  # 5 minutes = 300 seconds
        
    else:
        # Unauthorized motion - full security response
        log_event("SECURITY ALERT: Unauthorized motion detected!")
        
        if is_dark():
            light_on()
        
        buzzer_on()
        image_path = capture_image("intruder_motion")
        
        # Send security alert
        send_sms(f"SECURITY ALERT: Unauthorized motion detected at {time.strftime('%Y-%m-%d %H:%M:%S')}")
        if image_path:
            send_image_mms(image_path, "INTRUDER ALERT - Motion detected")
        
        # Turn off buzzer and light after 30 seconds for intruders
        def reset_actuators():
            buzzer_off()
            light_off()
            log_event("Security actuators reset after intruder alert")
        
        Timer(30, reset_actuators).start()

def start_motion_monitor():
    pir1.when_motion = motion_worker
    pir2.when_motion = motion_worker

# === Temp & Humidity (DHT22) ===
DHT_PIN = 5
DHT_SENSOR = Adafruit_DHT.DHT22

def read_temp_humidity():
    humidity, temperature = Adafruit_DHT.read_retry(DHT_SENSOR, DHT_PIN)
    if humidity is not None and temperature is not None:
        log_event(f"Temp: {temperature:.1f}°C, Humidity: {humidity:.1f}%")
        return temperature, humidity
    else:
        log_event("Failed to read DHT sensor")
        return None, None

# === Flame Sensor ===
flame_sensor = DigitalInputDevice(6)

def read_flame():
    try:
        if flame_sensor.value == 0:  # active LOW
            log_event("🔥 Flame detected!")
            return True
        return False
    except Exception as e:
        log_event(f"Flame sensor error: {e}")
        return False

# === Smoke Sensor (ADS1115 ADC) ===
import board
import busio
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn

i2c = busio.I2C(board.SCL, board.SDA)
ads = ADS.ADS1115(i2c)
mq_channel = AnalogIn(ads, ADS.P0)

SMOKE_THRESHOLD = None  # set after calibration
CALIBRATION_TIME = 30   # seconds

def read_smoke():
    try:
        val = (mq_channel.voltage / ads.gain) if ads.gain else mq_channel.voltage
        log_event(f"Smoke sensor voltage: {mq_channel.voltage:.3f}V (raw={mq_channel.value})")
        return val
    except Exception as e:
        log_event(f"MQ sensor read error: {e}")
        return None

def calibrate_smoke_sensor():
    """Measure baseline in clean air and set threshold."""
    global SMOKE_THRESHOLD
    log_event("Calibrating smoke sensor... Keep sensor in clean air.")
    readings = []
    start_time = time()
    while time() - start_time < CALIBRATION_TIME:
        val = read_smoke()
        if val is not None:
            readings.append(val)
        sleep(1)
    if readings:
        baseline = sum(readings) / len(readings)
        SMOKE_THRESHOLD = baseline + 0.2  # add margin
        log_event(f"Smoke sensor calibrated. Baseline={baseline:.3f}, Threshold={SMOKE_THRESHOLD:.3f}")
    else:
        SMOKE_THRESHOLD = 1.0  # fallback
        log_event("Calibration failed, using default threshold=1.0V")

# === Environment Monitoring ===
def monitor_environment(interval=2):
    """Continuously monitor temp, humidity, smoke, flame."""
    if SMOKE_THRESHOLD is None:
        calibrate_smoke_sensor()

    while True:
        temp, hum = read_temp_humidity()
        smoke_val = read_smoke()
        flame_detected = read_flame()

        if smoke_val is not None and smoke_val > SMOKE_THRESHOLD:
            log_event("🚨 Smoke threshold exceeded! Triggering alarm!")
            buzzer_on()
            light_on()
            image_path = capture_image("smoke_alert")
            
            # Send emergency alert regardless of user authorization
            send_sms(f"EMERGENCY: Smoke detected at {time.strftime('%Y-%m-%d %H:%M:%S')}")
            if image_path:
                send_image_mms(image_path, "EMERGENCY - Smoke detected")
            
            sleep(5)
            buzzer_off()
            light_off()

        if flame_detected:
            log_event("🚨 Flame detected! Triggering alarm!")
            buzzer_on()
            light_on()
            image_path = capture_image("flame_alert")
            
            # Send emergency alert regardless of user authorization
            send_sms(f"EMERGENCY: Flame detected at {time.strftime('%Y-%m-%d %H:%M:%S')}")
            if image_path:
                send_image_mms(image_path, "EMERGENCY - Flame detected")
            
            sleep(5)
            buzzer_off()
            light_off()

        sleep(interval)

def start_environment_monitor():
    t_env = Thread(target=monitor_environment, args=(2,), daemon=True)
    t_env.start()
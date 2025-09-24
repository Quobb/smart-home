from gpiozero import MotionSensor, MCP3008
from threading import Thread, Timer
from actuators import light_on, light_off, buzzer_on, buzzer_off
from camera_module import capture_image, is_dark
import Adafruit_DHT
from time import sleep
from utils import log_event

# === Motion Sensors ===
pir1 = MotionSensor(23)
pir2 = MotionSensor(24)

def motion_worker():
    log_event("Motion detected")
    if is_dark():
        light_on()
    buzzer_on()
    capture_image("motion")
    
    # Turn off buzzer and light after 5 sec
    def reset_actuators():
        buzzer_off()
        light_off()
    Timer(5, reset_actuators).start()

def start_motion_monitor():
    pir1.when_motion = motion_worker
    pir2.when_motion = motion_worker

# === Humidity/Temperature ===
DHT_PIN = 4
DHT_SENSOR = Adafruit_DHT.DHT22

# === Smoke sensor ===
mq_sensor = MCP3008(channel=0)
SMOKE_THRESHOLD = 0.35  # adjust experimentally

def read_temp_humidity():
    humidity, temperature = Adafruit_DHT.read_retry(DHT_SENSOR, DHT_PIN)
    if humidity is not None and temperature is not None:
        log_event(f"Temp: {temperature:.1f}C, Humidity: {humidity:.1f}%")
        return temperature, humidity
    else:
        log_event("Failed to read DHT sensor")
        return None, None

def read_smoke():
    try:
        val = mq_sensor.value  # normalized 0..1
        log_event(f"Smoke sensor value: {val:.3f}")
        return val
    except Exception as e:
        log_event(f"MQ sensor read error: {e}")
        return None

def monitor_environment(interval=10):
    """Continuously monitor temp, humidity, smoke."""
    while True:
        temp, hum = read_temp_humidity()
        smoke_val = read_smoke()
        if smoke_val is not None and smoke_val > SMOKE_THRESHOLD:
            log_event("Smoke threshold exceeded! Trigger alarm!")
            buzzer_on()
            light_on()
            capture_image("smoke_alert")
            # Here you can add SMS/GSM alert
            sleep(5)
            buzzer_off()
            light_off()
        sleep(interval)

def start_environment_monitor():
    t_env = Thread(target=monitor_environment, args=(10,), daemon=True)
    t_env.start()

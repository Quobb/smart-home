from gpiozero import MotionSensor, DigitalInputDevice
from threading import Thread, Timer
from actuators import light_on, light_off, buzzer_on, buzzer_off
from camera_module import capture_image, is_dark
import Adafruit_DHT
from time import sleep, time
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
        # Normalized value 0..1 (ADS1115 is 16-bit ± voltage)
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
            capture_image("smoke_alert")
            sleep(5)
            buzzer_off()
            light_off()

        if flame_detected:
            buzzer_on()
            light_on()
            capture_image("flame_alert")
            sleep(5)
            buzzer_off()
            light_off()

        sleep(interval)


def start_environment_monitor():
    t_env = Thread(target=monitor_environment, args=(2,), daemon=True)
    t_env.start()

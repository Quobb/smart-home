from gpiozero import MotionSensor, DigitalInputDevice
from time import sleep

# === Flame Sensor ===
flame_sensor = DigitalInputDevice(6)

def read_flame():
    try:
        if flame_sensor.value == 0:  # active LOW
            print("🔥 Flame detected!")
            return True
        else:
            print("No flame detected")
            return False
    except Exception as e:
        print(f"Flame sensor error: {e}")
        return False

# Continuous monitoring
while True:
    read_flame()
    sleep(1)

# === GSM Config ===
GSM_SERIAL_PORT = "/dev/serial0"
GSM_BAUDRATE = 9600   # SIM800L default

   # or "/dev/serial0" depending on Pi model

# === Pin configuration ===
PIN_SERVO = 16      # Servo (GPIO16 / Pin36)
PIN_PIR1 = 23       # PIR sensor 1
PIN_PIR2 = 24       # PIR sensor 2
PIN_LIGHT = 27      # DC bulb
PIN_BUZZER = 26
PIN_BUZZER_2 = 17
PIN_RFID_IRQ = 25   # RFID IRQ (pin37)

# === Servo positions ===
SERVO_OPEN_DC = 1
SERVO_CLOSED_DC = -1

# === Motion detection hours ===
MOTION_ARM_HOUR_START = 22
MOTION_ARM_HOUR_END = 6

# === Camera ===
CAMERA_INDEX = 0
BRIGHTNESS_THRESHOLD = 50

# === Logs ===
LOG_DIR = "/home/malware/smart_home_logs"

# === SMS recipients ===
ALERT_PHONE_NUMBERS = ["+233552915020"]

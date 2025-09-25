from gpiozero import LED,Buzzer,MotionSensor,Servo
from signal import pause
from time import sleep
servo = Servo(16)

servo.value = 1
sleep(1)
servo.value = None


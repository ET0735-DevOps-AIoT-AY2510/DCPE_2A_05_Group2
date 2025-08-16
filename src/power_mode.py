import time
import threading
import RPi.GPIO as GPIO
from hal import hal_keypad as keypad
from hal import hal_lcd as lcd
from hal import hal_usonic as usonic

# Constant
INACTIVITY_TIMEOUT = 8 # 3 minutes original (in seconds)
ULTRASONIC_RANGE = 10
# Global variables
last_keypress_time = time.time()
last_ultrasonic_detect_time = time.time()

# Initialization
lcd_instance = lcd.lcd()
keypad.init(None)
usonic.init()

# State
power_state = False

#High Power Mode
def high_power_mode():
    global power_state
    if power_state != True :
        lcd_instance.backlight(1)
        print("High Power Mode activated")
        power_state = True
    return power_state

#Low Power Mode
def low_power_mode():
    global power_state
    if power_state != False:
        lcd_instance.backlight(0)
        print("Low Power Mode activated")
        power_state = False
    return power_state

#Key detection 1
def key_press_callback(key):
    global last_keypress_time
    last_keypress_time = time.time()
    high_power_mode()
    
    #Power off 'key'
    if key == '*': 
        print("Low Power Mode button pressed.")
        low_power_mode()

#Inactivity detection
def monitor_inactivity():
    global last_keypress_time, last_ultrasonic_detect_time
    while True:
        now = time.time()
        time_since_keypress = now - last_keypress_time
        time_since_ultrasonic = now - last_ultrasonic_detect_time

        if time_since_keypress >= INACTIVITY_TIMEOUT and time_since_ultrasonic >= INACTIVITY_TIMEOUT:
            low_power_mode()

        time.sleep(1)

#keypad detection 2
def detect_keypad():
    keypad.init(key_press_callback)
    while True:
        keypad.get_key()
        time.sleep(0.1)

#displaying of ultrasonic reading
def monitor_ultrasonic():
    global last_ultrasonic_detect_time
    while True:
        distance = usonic.get_distance()
        print(f"Ultrasonic distance: {distance:.2f} cm")

    #ultrasonic threshold range
        if distance < ULTRASONIC_RANGE:
            last_ultrasonic_detect_time = time.time()
            high_power_mode()

        time.sleep(1)

def main():
    threading.Thread(target=monitor_inactivity, daemon=True).start() #threading
    threading.Thread(target=monitor_ultrasonic, daemon=True).start()
    threading.Thread(target=detect_keypad, daemon=True).start()

    while True:
        time.sleep(1)


if __name__ == '__main__':
    main()

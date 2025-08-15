import time
import threading
import RPi.GPIO as GPIO
from hal import hal_keypad as keypad
from hal import hal_lcd as lcd
from hal import hal_usonic as usonic

# Constants
INACTIVITY_TIMEOUT = 20  # seconds
ULTRASONIC_RANGE = 10   # cm

# Globals
last_keypress_time = time.time()
last_ultrasonic_detect_time = time.time()
power_state = False

# Shared thread-safe flags
low_power_event = threading.Event()
high_power_event = threading.Event()
staff_access_event = threading.Event()

# Power mode switching
def high_power_mode():
    lcd_instance.backlight(1)
    print("High Power Mode activated")
    low_power_event.clear()
    high_power_event.set()

def low_power_mode():
    lcd_instance.backlight(0)
    print("Low Power Mode activated")
    high_power_event.clear()
    low_power_event.set()

# Keypad interaction
# def key_press_callback(key):
#     global last_keypress_time
#     last_keypress_time = time.time()
#     high_power_mode()

#     if key == 0:
#         print("Low Power Mode button pressed.")
#         low_power_mode()

def monitor_inactivity():
    global last_keypress_time, last_ultrasonic_detect_time
    while True:
        if not staff_access_event.is_set():
            now = time.time()
            time_since_key = now - last_keypress_time
            time_since_ultra = now - last_ultrasonic_detect_time
# time_since_key >= INACTIVITY_TIMEOUT and
            if  time_since_ultra >= INACTIVITY_TIMEOUT:
                low_power_mode()

        time.sleep(1)

# def detect_keypad():
#     keypad.init(key_press_callback)
#     while True:
#         if not staff_access_event.is_set():
#             keypad.get_key()
#         time.sleep(0.1)

def monitor_ultrasonic():
    global last_ultrasonic_detect_time
    while True:
        if not staff_access_event.is_set():
            distance = usonic.get_distance()
            print(f"Ultrasonic distance: {distance:.2f} cm")

            if distance < ULTRASONIC_RANGE:
                last_ultrasonic_detect_time = time.time()
                high_power_mode()

        time.sleep(1)

def monitor_power():
    global lcd_instance
    lcd_instance = lcd.lcd()
    # keypad.init(None)
    usonic.init()
    threading.Thread(target=monitor_inactivity, daemon=True).start()
    # threading.Thread(target=detect_keypad, daemon=True).start()
    threading.Thread(target=monitor_ultrasonic, daemon=True).start()

# For standalone testing
if __name__ == '__main__':
    monitor_power()
    while True:
        time.sleep(1)

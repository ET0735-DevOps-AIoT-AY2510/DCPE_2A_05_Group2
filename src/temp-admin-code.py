
from hal import hal_temp_humidity_sensor as temphumi
from hal import hal_servo as servo
import RPi.GPIO as GPIO
from time import sleep
import time
from hal import dht11
import threading

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

# --- Servo Setup ---
SERVO_PIN = 26
GPIO.setup(SERVO_PIN, GPIO.OUT)
servo_pwm = GPIO.PWM(SERVO_PIN, 50)
servo_pwm.start(0)

# --- Keypad Setup ---
MATRIX = [[1, 2, 3],
          [4, 5, 6],
          [7, 8, 9],
          ['*', 0, '#']]
ROW = [6, 20, 19, 13]
COL = [12, 5, 16]

VALID_CODE = "1234"
entered_code = []

# Globals
cbk_func = None
dht11_inst = None
monitoring_started = False  # Flag to prevent restarting the thread


# --- DHT11 Setup ---
def init_dht_sensor():
    global dht11_inst
    dht11_inst = dht11.DHT11(pin=21)

def read_temp_humidity():
    time.sleep(2)
    global dht11_inst
    result = dht11_inst.read()

    if result.is_valid():
        temperature = result.temperature
        humidity = result.humidity
        print(f"\nTemperature: {temperature:.1f}°C, Humidity: {humidity:.1f}%")
        if temperature < 1.6 or temperature > 4.4:
            print("Temperature out of safe range!")
        return [temperature, humidity]
    else:
        print("Failed to read from DHT11 sensor.")
        return [-100, -100]

def monitor_temp_continuously():
    while True:
        read_temp_humidity()
        sleep(5)


# --- Keypad Setup ---
def init_keypad(key_press_cbk):
    global cbk_func
    cbk_func = key_press_cbk

    for i in range(3):
        GPIO.setup(COL[i], GPIO.OUT)
        GPIO.output(COL[i], 1)

    for j in range(4):
        GPIO.setup(ROW[j], GPIO.IN, pull_up_down=GPIO.PUD_UP)

def get_key():
    global cbk_func
    while True:
        for i in range(3):
            GPIO.output(COL[i], 0)
            for j in range(4):
                if GPIO.input(ROW[j]) == 0:
                    cbk_func(MATRIX[j][i])
                    while GPIO.input(ROW[j]) == 0:
                        sleep(0.1)
            GPIO.output(COL[i], 1)

# --- Servo and Sensor Start ---
def actuate_servo_and_start_monitor():
    global monitoring_started

    print("\nAccess Granted: Opening door...")
    servo_pwm.ChangeDutyCycle(7)
    sleep(2)
    servo_pwm.ChangeDutyCycle(0)

    if not monitoring_started:
        print("Starting continuous temperature monitoring...")
        monitoring_started = True
        thread = threading.Thread(target=monitor_temp_continuously, daemon=True)
        thread.start()


# --- Keypad Handling ---
def on_key_press(key):
    global entered_code

    if key == '#':
        entered_code_str = ''.join(map(str, entered_code))
        if entered_code_str == VALID_CODE:
            actuate_servo_and_start_monitor()
        else:
            print("Wrong Code!")
        entered_code = []

    elif key == '*':
        entered_code = []
        print("Code cleared")

    else:
        if str(key).isdigit():
            entered_code.append(str(key))
            print(f"\rEntered so far: {''.join(entered_code)}", end='', flush=True)

            if len(entered_code) == len(VALID_CODE):
                entered_code_str = ''.join(entered_code)
                if entered_code_str == VALID_CODE:
                    actuate_servo_and_start_monitor()
                else:
                    print("Wrong Code!")
                entered_code = []


# --- Start Program ---
try:
    init_dht_sensor()
    time.sleep(2)  # allow sensor to stabilize
    init_keypad(on_key_press)
    print("Enter code on keypad:")
    get_key()

except KeyboardInterrupt:
    print("\nCleaning up GPIO...")
finally:
    servo_pwm.stop()
    GPIO.cleanup()

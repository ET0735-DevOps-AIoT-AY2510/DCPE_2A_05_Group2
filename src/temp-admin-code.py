
from hal import hal_temp_humidity_sensor as temphumi
from hal import hal_servo as servo
import RPi.GPIO as GPIO
from time import sleep
import time
from hal import dht11
import threading
from hal import hal_lcd  # If your LCD code is in a file named lcd_driver.py
lcd_display = hal_lcd.lcd()
lcd_display.lcd_display_string("Enter code:".ljust(16), line=1)

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
code_valid = False
entered_code = []

# Globals
cbk_func = None
dht11_inst = None
monitoring_started = False  # Flag to prevent restarting the thread
code_valid == False

# initialise slide switch and setup

# --- DHT11 Setup ---
def init_dht_sensor():
     global dht11_inst
     time.sleep(2)
     dht11_inst = dht11.DHT11(pin=21)
    # ----
def read_temp_humidity():
    global dht11_inst
    sleep(2)
    result = dht11_inst.read()
    print("Starting temperature monitoring...")
    if result.is_valid():
        temperature = result.temperature
        humidity = result.humidity
        sleep(1)
        lcd_display.lcd_display_string(f"Temp: {temperature:.1f}C", line=1)
        print(f"Temperature: {temperature:.1f}°C, Humidity: {humidity:.1f}%")

        if temperature < 1.6 or temperature > 4.4:
            lcd_display.lcd_display_string("WARNING!", line=2)
            sleep(2)
            lcd_display.lcd_display_string(" " * 16, line=2)
        else:
            lcd_display.lcd_display_string(" " * 16, line=2)  # Clear warning

        return [temperature, humidity]

    else:
        print("Sensor read fail")
        lcd_display.lcd_display_string("Sensor read fail", line=2)
        return [-100, -100]
    
def monitor_temp_continuously():
    while True:
        read_temp_humidity()
        sleep(2)


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
def actuate_servo():
    servo_pwm.ChangeDutyCycle(8)
    sleep(1)
    servo_pwm.ChangeDutyCycle(0)
    sleep(3)
    servo_pwm.ChangeDutyCycle(2)
    sleep(2)

      # Clear again to prepare for temp display after door opens
    lcd_display.lcd_clear()
    
    # Start temperature monitoring thread (daemon=True so it stops on program exit)
    threading.Thread(target=monitor_temp_continuously, daemon=True).start()

# --- Keypad Handling ---
def on_key_press(key):
    global entered_code,code_valid

    if code_valid:
        return

    if key == '#':
        code = ''.join(entered_code)
        if code == VALID_CODE:
            code_valid = True
            lcd_display.lcd_clear()
            lcd_display.lcd_display_string("Access Granted!", line=1)
            sleep(2)
            actuate_servo()
        else:
            lcd_display.lcd_display_string("Wrong Code!", line=2)
            sleep(2)
            lcd_display.lcd_display_string("Enter code:", line=1)
            lcd_display.lcd_display_string(" " * 16, line=2)  # clear second line
            entered_code = []

    elif key == '*':
        entered_code = []
        lcd_display.lcd_display_string("Enter code:", line=1)
        lcd_display.lcd_display_string(" " * 16, line=2)

    elif str(key).isdigit():
        if len(entered_code) < 4:  # Limit input to 4 digits
            entered_code.append(str(key))
            lcd_display.lcd_display_string(f"Enter code:{''.join(entered_code):<4}", line=1)
            if len(entered_code) == len(VALID_CODE):
                on_key_press('#')  # Auto-submit


# --- Start Program ---
try:
    lcd_display.lcd_clear()
    dht11_inst = dht11.DHT11(pin=21)
    time.sleep(2)
    init_keypad(on_key_press)
    lcd_display.lcd_display_string("Enter code:".ljust(16), line=1)
    get_key()

   
        
    

except KeyboardInterrupt:
    print("\nPowering down...")
finally:
    servo_pwm.stop()
    GPIO.cleanup()

from hal import hal_temp_humidity_sensor as temphumi
from hal import hal_lcd
from hal import hal_ir_sensor as ir_sensor
from hal import hal_buzzer as buzzer
import RPi.GPIO as GPIO
from time import sleep
import time
from hal import dht11
import threading
from threading import Thread
import os
import datetime
from PIL import Image
from io import BytesIO
import requests
from picamera2 import Picamera2
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import subprocess

# ===== CONFIG =====
TOKEN = "8242655620:AAFPEAtnxfRjwPnp6J7t3kEMFSp5w94Yujw"
chat_id = "5043247672"

sender_email = "vmoperations3@gmail.com"
password = "tucq kspl jryl brnv"
recipient_emails = ["matinaryan06@gmail.com","shirohskates@gmail.com"]
subject_template = "Hello, {name}!"
body_template = """To all Vending Machine Admins,

The vending machine requires assistance as its temperature has fallen out of the optimal range.

Best regards,
The Team at DevOps Vending Machine
"""

LOCAL_SAVE_PATH = "/home/pi/ET0735/burglar_images"
if not os.path.exists(LOCAL_SAVE_PATH):
    os.makedirs(LOCAL_SAVE_PATH)

# ===== LCD =====
lcd_display = hal_lcd.lcd()
lcd_display.lcd_display_string("Temp Monitoring...", line=1)

# ===== GPIO =====
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

# ===== SERVO =====
SERVO_PIN = 26
GPIO.setup(SERVO_PIN, GPIO.OUT)
servo_pwm = GPIO.PWM(SERVO_PIN, 50)
servo_pwm.start(0)

# ===== KEYPAD =====
MATRIX = [[1, 2, 3],[4, 5, 6],[7, 8, 9],['*', 0, '#']]
ROW = [6, 20, 19, 13]
COL = [12, 5, 16]

VALID_CODE = "1234"
entered_code = []
code_active = False
door_opened = False
temperature_paused = False
burglar_paused = False
cbk_func = None
dht11_inst = None

# ===== CAMERA =====
camera = Picamera2()
camera.preview_configuration.main.size = (640,480)
camera.preview_configuration.main.format = "RGB888"
camera.configure("preview")
camera.start()
print("Camera initialized with 640x480 RGB888")

# ===== HELPER FUNCTIONS =====
def capture_image():
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"burglar_{timestamp}.jpg"
    filepath = os.path.join(LOCAL_SAVE_PATH, filename)
    try:
        frame = camera.capture_array()
        img = Image.fromarray(frame)
        img.save(filepath)
        print(f"Image saved at {filepath}")
        return filepath
    except Exception as e:
        print(f"[ERROR] Camera capture failed: {e}")
        return None

def send_telegram_text(message):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        params = {'chat_id': chat_id,'text': message}
        resp = requests.get(url, params=params)
        print("Telegram message sent:", resp.json())
    except Exception as e:
        print(f"[ERROR] Telegram text failed: {e}")

def send_telegram_image(image_path):
    try:
        img = Image.open(image_path)
        image_stream = BytesIO()
        img.save(image_stream, format='PNG')
        image_stream.seek(0)
        url = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
        files = {'photo': ('image.png', image_stream)}
        data = {'chat_id': chat_id}
        resp = requests.post(url, files=files, data=data)
        print("Telegram image sent:", resp.json())
    except Exception as e:
        print(f"[ERROR] Telegram image failed: {e}")

def send_email_alert():
    for recipient in recipient_emails:
        name = recipient.split("@")[0]
        message = MIMEMultipart()
        message["From"] = sender_email
        message["To"] = recipient
        message["Subject"] = subject_template.format(name=name.capitalize())
        message.attach(MIMEText(body_template.format(name=name.capitalize()), "plain"))
        try:
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                server.login(sender_email,password)
                server.sendmail(sender_email,recipient,message.as_string())
                print(f"Email sent to {recipient}")
        except Exception as e:
            print(f"[ERROR] Email failed: {e}")

# ===== MONITORS =====
def monitor_door():
    global burglar_paused
    while True:
        if not burglar_paused:
            ir_value = ir_sensor.get_ir_sensor_state()
            if ir_value is False:
                print("Burglar detected!")
                send_telegram_text("Burglar Detected!")
                image_path = capture_image()
                if image_path:
                    send_telegram_image(image_path)
        sleep(2)

def init_dht_sensor():
    global dht11_inst
    dht11_inst = dht11.DHT11(pin=21)
    time.sleep(2)

def monitor_temp():
    global dht11_inst, temperature_paused
    if dht11_inst is None:
        init_dht_sensor()
    while True:
        if not temperature_paused:
            result = dht11_inst.read()
            if result.is_valid():
                temp = result.temperature
                hum = result.humidity
                lcd_display.lcd_display_string(f"Temp:{temp:.1f}C Hum:{hum:.1f}%", line=1)
                if temp<1.6 or temp>4.4:
                    print("Temperature out of range!")
                    send_telegram_text("Temperature out of range!")
                    send_email_alert()
        sleep(2)

# ===== KEYPAD & SERVO =====
def init_keypad(cbk):
    global cbk_func
    cbk_func = cbk
    for i in range(3):
        GPIO.setup(COL[i],GPIO.OUT)
        GPIO.output(COL[i],1)
    for j in range(4):
        GPIO.setup(ROW[j],GPIO.IN,pull_up_down=GPIO.PUD_UP)

def get_key():
    global cbk_func
    while True:
        for i in range(3):
            GPIO.output(COL[i],0)
            for j in range(4):
                if GPIO.input(ROW[j])==0:
                    cbk_func(MATRIX[j][i])
                    while GPIO.input(ROW[j])==0:
                        sleep(0.1)
            GPIO.output(COL[i],1)

def actuate_servo(open_door=True):
    if open_door:
        servo_pwm.ChangeDutyCycle(8)
        sleep(1)
        servo_pwm.ChangeDutyCycle(0)
    else:
        servo_pwm.ChangeDutyCycle(2)
        sleep(2)
        servo_pwm.ChangeDutyCycle(0)

def on_key_press(key):
    global entered_code, code_active, door_opened, temperature_paused, burglar_paused

    if key == '#':
        code_active = True
        temperature_paused = True
        burglar_paused = True
        entered_code.clear()
        lcd_display.lcd_display_string("Enter code:".ljust(16), line=1)

    elif key == '*':
        if door_opened:
            lcd_display.lcd_display_string("Door Closing".ljust(16), line=1)
            actuate_servo(open_door=False)
            door_opened = False
        temperature_paused = False
        burglar_paused = False
        sleep(2)

    elif code_active and str(key).isdigit():
        if len(entered_code)<4:
            entered_code.append(str(key))
            lcd_display.lcd_display_string(f"Enter code:{''.join(entered_code):<4}", line=1)
            if len(entered_code)==4:
                code = ''.join(entered_code)
                if code==VALID_CODE:
                    lcd_display.lcd_display_string("Access Granted!".ljust(16), line=1)
                    actuate_servo(open_door=True)
                    door_opened=True
                    # Resume temperature display immediately
                    temperature_paused = False
                    burglar_paused = False
                else:
                    lcd_display.lcd_display_string("Wrong Code!".ljust(16), line=1)
                    sleep(1)
                entered_code.clear()
                code_active=False


# ===== MAIN =====
def main():
    ir_sensor.init()
    buzzer.init()
    Thread(target=monitor_door, daemon=True).start()
    Thread(target=monitor_temp, daemon=True).start()
    init_keypad(on_key_press)
    Thread(target=get_key, daemon=True).start()
    while True:
        sleep(1)

try:
    main()
except KeyboardInterrupt:
    print("\nShutting down...")
finally:
    servo_pwm.stop()
    GPIO.cleanup()

from hal import hal_temp_humidity_sensor as temphumi
from hal import hal_servo as servo
import RPi.GPIO as GPIO
from time import sleep
import time
from hal import dht11
import threading
from hal import hal_lcd  
from threading import Thread
import os
import datetime
import paramiko  # For SCP transfer to laptop (optional)
from PIL import Image
from io import BytesIO
import requests
from hal import hal_ir_sensor as ir_sensor
from hal import hal_buzzer as buzzer

from picamera import PiCamera

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ===== Telegram Bot Config =====
TOKEN = "8242655620:AAFPEAtnxfRjwPnp6J7t3kEMFSp5w94Yujw"
chat_id = "5043247672"

# ===== Email Config =====
sender_email = "vmoperations3@gmail.com"
password = "tucq kspl jryl brnv"

recipient_emails = [
    "matinaryan06@gmail.com",
    "shirohskates@gmail.com"
]

subject_template = "Hello, {name}!"
body_template = """To all Vending Machine Admins,

The vending machine requires assistance as its temperature has fallen out of the optimal range.

Best regards,
The Team at DevOps Vending Machine
"""

# ===== CAMERA SETUP =====
camera = PiCamera()
camera.resolution = (1024, 768)
sleep(2)  # Camera warm-up delay

# ===== BURGLAR IMAGE SAVE SETTINGS =====
LOCAL_SAVE_PATH = "/home/pi/burglar_images"  # Pi storage location
LAPTOP_USER = "Stickman"
LAPTOP_IP = "192.168.18.59"   # Laptop IP in same network
LAPTOP_PATH = r"C:\Local_Git_Repository\DCPE_2A_05_Group2\picam"  # Windows path raw string

if not os.path.exists(LOCAL_SAVE_PATH):
    os.makedirs(LOCAL_SAVE_PATH)

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


def capture_and_transfer_image():
    """Capture an image and transfer it to laptop via SCP."""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"burglar_{timestamp}.jpg"
    filepath = os.path.join(LOCAL_SAVE_PATH, filename)

    try:
        camera.capture(filepath)
        print(f"Image saved locally at {filepath}")
    except Exception as e:
        print(f"[ERROR] Camera capture failed: {e}")
        return None

    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        # Use SSH key auth for better security instead of password
        ssh.connect(LAPTOP_IP, username=LAPTOP_USER, password="your_password")

        sftp = ssh.open_sftp()
        sftp.put(filepath, os.path.join(LAPTOP_PATH, filename))
        sftp.close()
        ssh.close()
        print("Image transferred to laptop.")
    except Exception as e:
        print(f"[ERROR] Could not transfer image: {e}")

    return filepath


def send_telegram_alert(image_path=None, message="Vending Machine requires maintenance!"):
    """Send alert message and optionally image via Telegram bot."""

    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        params = {'chat_id': chat_id, 'text': message}
        resp = requests.get(url, params=params)
        print(f"Telegram message response: {resp.json()}")
    except Exception as e:
        print(f"[ERROR] Sending Telegram message failed: {e}")

    if image_path:
        try:
            img = Image.open(image_path)
            image_stream = BytesIO()
            img.save(image_stream, format='PNG')
            image_stream.seek(0)

            url = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
            files = {'photo': ('image.png', image_stream)}
            data = {'chat_id': chat_id}
            resp = requests.post(url, files=files, data=data)
            print(f"Telegram photo response: {resp.json()}")
        except Exception as e:
            print(f"[ERROR] Sending Telegram photo failed: {e}")


def send_email_alert():
    for recipient in recipient_emails:
        name = recipient.split("@")[0]
        message = MIMEMultipart()
        message["From"] = sender_email
        message["To"] = recipient
        message["Subject"] = subject_template.format(name=name.capitalize())

        body = body_template.format(name=name.capitalize())
        message.attach(MIMEText(body, "plain"))

        try:
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                server.login(sender_email, password)
                server.sendmail(sender_email, recipient, message.as_string())
                print(f"Email sent to {recipient}")
        except Exception as e:
            print(f"Error sending to {recipient}: {e}")


def monitor_door(paid, staff_access):
    while True:
        ir_value = ir_sensor.get_ir_sensor_state()
        time.sleep(2)
        print("IR Sensor State:", ir_value)

        if ir_value is False and not paid and not staff_access:
            print("Burglar detected!")
            lcd_display.lcd_display_string("BURGLAR ALERT!", line=1)
            buzzer.beep(0.5, 0.5, 10)
            captured_file = capture_and_transfer_image()
            send_telegram_alert(captured_file, "Burglar detected! Here’s the snapshot.")
            time.sleep(2)


def init_dht_sensor():
    global dht11_inst
    time.sleep(2)
    dht11_inst = dht11.DHT11(pin=21)


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
            alert_image = os.path.join(LOCAL_SAVE_PATH, "temp_alert.jpg")

            try:
                camera.capture(alert_image)
            except Exception as e:
                print(f"[ERROR] Failed to capture temperature alert image: {e}")

            # Send Telegram + Email alerts
            send_telegram_alert(image_path=alert_image, message="Vending Machine temperature out of range!")
            send_email_alert()
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


def actuate_servo():
    servo_pwm.ChangeDutyCycle(8)
    sleep(1)
    servo_pwm.ChangeDutyCycle(0)
    sleep(3)
    servo_pwm.ChangeDutyCycle(2)
    sleep(2)

    lcd_display.lcd_clear()

    threading.Thread(target=monitor_temp_continuously, daemon=True).start()


def on_key_press(key):
    global entered_code, code_valid

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
            lcd_display.lcd_display_string(" " * 16, line=2)
            entered_code.clear()

    elif key == '*':
        entered_code.clear()
        lcd_display.lcd_display_string("Enter code:", line=1)
        lcd_display.lcd_display_string(" " * 16, line=2)

    elif str(key).isdigit():
        if len(entered_code) < 4:
            entered_code.append(str(key))
            lcd_display.lcd_display_string(f"Enter code:{''.join(entered_code):<4}", line=1)
            if len(entered_code) == len(VALID_CODE):
                on_key_press('#')  # Auto-submit


def main():
    ir_sensor.init()
    buzzer.init()
    paid = False
    staff_access = False

    door_thread = Thread(target=monitor_door, args=(paid, staff_access), daemon=True)
    door_thread.start()


try:
    main()
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

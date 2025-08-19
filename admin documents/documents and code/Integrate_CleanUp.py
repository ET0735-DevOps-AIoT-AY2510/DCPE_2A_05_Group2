import os
import time
import datetime
import threading
from time import sleep
from typing import Optional

import RPi.GPIO as GPIO
from PIL import Image
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from picamera2 import Picamera2
from hal import dht11
from hal import hal_buzzer as buzzer

# ============
# CONFIG
# ============
burglar_detect = threading.Event()  # set this from other modules to trigger alert

# Telegram
TOKEN = "8242655620:AAFPEAtnxfRjwPnp6J7t3kEMFSp5w94Yujw"
CHAT_IDS = ["5043247672", "-1002502383796"]

# Email (use an app password)
SENDER_EMAIL = "vmoperations3@gmail.com"
SENDER_PASS  = "tucq kspl jryl brnv"
RECIPIENTS   = ["titussohpx@gmail.com", "spxt.24@ichat.sp.edu.sg"]
SUBJECT      = "Vending Machine Temperature Alert"
BODY         = (
    "To all Vending Machine Admins,\n\n"
    "The vending machine requires assistance as its temperature has fallen out of the optimal range.\n\n"
    "Best regards,\n"
    "The Team at DevOps Vending Machine\n"
)

# Thresholds & cooldowns
TEMP_MIN_C = 1.6
TEMP_MAX_C = 4.4
TEMP_EMAIL_COOLDOWN_S = 30   # avoid spamming email if temp stays bad
BURGLAR_COOLDOWN_S     = 10  # avoid spamming telegram on repeated triggers

# Storage for captured images
LOCAL_SAVE_PATH = "/home/pi/ET0735/burglar_images"
os.makedirs(LOCAL_SAVE_PATH, exist_ok=True)

# ============
# GLOBALS
# ============
dht = None
_last_temp_email_ts = 0.0
_last_burglar_ts    = 0.0

# If other processes also use the camera, they can collide. We’ll retry quickly.
def _capture_image_once() -> Optional[str]:
    cam = None
    try:
        cam = Picamera2()
        cam.preview_configuration.main.size = (640, 480)
        cam.preview_configuration.main.format = "RGB888"
        cam.configure("preview")
        cam.start()
        time.sleep(0.2)  # tiny warm-up
        frame = cam.capture_array()
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join(LOCAL_SAVE_PATH, f"burglar_{ts}.jpg")
        Image.fromarray(frame).save(path, format="JPEG")
        return path
    except Exception as e:
        print(f"[CAM] capture failed: {e}")
        return None
    finally:
        try:
            if cam:
                cam.stop()
        except Exception:
            pass
        try:
            if cam:
                cam.close()
        except Exception:
            pass

def capture_image(retries: int = 3, delay_s: float = 0.5) -> Optional[str]:
    """Try to capture with a few quick retries (handles ‘camera busy’ races)."""
    for attempt in range(1, retries + 1):
        path = _capture_image_once()
        if path:
            return path
        time.sleep(delay_s)
    return None

# ============
# HELPERS
# ============
def send_telegram_text(msg: str):
    for cid in CHAT_IDS:
        try:
            url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
            requests.get(url, params={"chat_id": cid, "text": msg}, timeout=8)
        except Exception as e:
            print(f"[TELEGRAM] text failed for {cid}: {e}")

def send_telegram_image(image_path: str):
    for cid in CHAT_IDS:
        try:
            with open(image_path, "rb") as f:
                url = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
                files = {"photo": (os.path.basename(image_path), f, "image/jpeg")}
                data  = {"chat_id": cid}
                requests.post(url, files=files, data=data, timeout=15)
        except Exception as e:
            print(f"[TELEGRAM] image failed for {cid}: {e}")

def send_email_alert(subject: str, body: str):
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=15) as server:
            server.login(SENDER_EMAIL, SENDER_PASS)
            for rcpt in RECIPIENTS:
                msg = MIMEMultipart()
                msg["From"] = SENDER_EMAIL
                msg["To"]   = rcpt
                msg["Subject"] = subject
                msg.attach(MIMEText(body, "plain"))
                server.sendmail(SENDER_EMAIL, rcpt, msg.as_string())
                print(f"[EMAIL] sent to {rcpt}")
    except Exception as e:
        print(f"[EMAIL] failed: {e}")

# ============
# MONITORS
# ============
def monitor_temp():
    """Email when temperature goes out of range (with cooldown)."""
    global _last_temp_email_ts, dht
    while True:
        try:
            result = dht.read()
            if result.is_valid():
                temp = float(result.temperature)
                hum  = float(result.humidity)
                print(f"[TEMP] {temp:.1f}C  {hum:.1f}%")

                out_of_range = (temp < TEMP_MIN_C) or (temp > TEMP_MAX_C)
                now = time.time()
                if out_of_range and (now - _last_temp_email_ts) >= TEMP_EMAIL_COOLDOWN_S:
                    send_email_alert(SUBJECT, BODY)
                    _last_temp_email_ts = now
            else:
                print("[TEMP] sensor error")
        except Exception as e:
            print(f"[TEMP] error: {e}")
        sleep(2)

def monitor_burglar():
    """Send Telegram alert + photo when burglar_detect is set (with cooldown)."""
    global _last_burglar_ts
    while True:
        if burglar_detect.is_set():
            now = time.time()
            if (now - _last_burglar_ts) >= BURGLAR_COOLDOWN_S:
                print("[BURGLAR] event detected")
                try:
                    buzzer.beep(0.3)
                except Exception:
                    pass
                send_telegram_text("Burglar Detected!")
                img = capture_image()
                if img:
                    send_telegram_image(img)
                _last_burglar_ts = now
            burglar_detect.clear()
        sleep(0.2)

# ============
# ENTRY
# ============
def main():
    global dht
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)

    dht = dht11.DHT11(pin=21)
    time.sleep(2)

    threading.Thread(target=monitor_temp, daemon=True).start()
    threading.Thread(target=monitor_burglar, daemon=True).start()

    while True:
        time.sleep(1)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        GPIO.cleanup()
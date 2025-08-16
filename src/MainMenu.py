# =========================
# Imports
# =========================
import time
import threading
from threading import Thread
import queue
from datetime import datetime

from database.seed_data import app
from hal import hal_keypad as keypad
from hal import hal_lcd as LCD
from hal import hal_input_switch as switch
from hal import hal_dc_motor as motor
from power_mode import (
    low_power_event,
    low_power_mode,
    high_power_event,
    staff_access_event,
    monitor_power,
    attach_lcd,
    ping_activity,
    request_low_power_with_guard,
)
import RFID as payment
import monitor_door_status as burglar_system
from PotentialMeter import MenuSelection, selection_finish_event, paid_event
from dcmotor import motor_spin
from paynow_ui import start_paynow_qr, stop_paynow_ui, paynow_success_event
from database.db_utils import load_products_from_db, update_stock_in_db

import admincode as admin
from admincode import session_done


# =========================
# Classes
# =========================
# Thread-safe wrapper around the LCD HAL to serialize writes
class SafeLCD:
    # Store the raw LCD object and set up a re-entrant lock
    def __init__(self, lcd):
        self._lcd = lcd
        self._lock = threading.RLock()

    # Write a padded 16-char string to the specified LCD line
    def lcd_display_string(self, s, line):
        s = str(s)[:16].ljust(16)
        with self._lock:
            self._lcd.lcd_display_string(s, line)

    # Clear the LCD display safely
    def lcd_clear(self):
        with self._lock:
            self._lcd.lcd_clear()


# =========================
# Globals / State
# =========================
Vending_Drinks = load_products_from_db()
shared_keypad_queue = queue.Queue()
stop_main_event = threading.Event()


# =========================
# Keypad Dispatch
# =========================
# Route keypad input, waking the system and forwarding to admin or user
def key_dispatch(key):
    try:
        if key not in (0, '0'):
            ping_activity()
    except Exception:
        pass

    if staff_access_event.is_set() and not session_done.is_set():
        try:
            admin.on_key_press(key)
        except Exception as e:
            print(f"[KEY DISPATCH] admin handler error: {e}")
        return

    shared_keypad_queue.put(key)


# =========================
# Startup
# =========================
# Initialize HALs, create/attach the shared LCD, and return a SafeLCD
def start():
    keypad.init(key_dispatch)
    switch.init()
    motor.init()

    real_lcd = LCD.lcd()
    try:
        real_lcd.backlight(0)
    except Exception:
        pass

    attach_lcd(real_lcd)
    lcd = SafeLCD(real_lcd)
    return lcd


# =========================
# Switch Monitor
# =========================
# Poll the admin/user switch and toggle mode flags accordingly
def monitor_switch():
    while True:
        input_val = switch.read_slide_switch()
        if input_val == 0:
            if not staff_access_event.is_set():
                print("[SWITCH] Admin mode ON")
                staff_access_event.set()
                stop_main_event.set()
        else:
            if staff_access_event.is_set() and session_done.is_set():
                print("[SWITCH] Admin mode OFF")
                staff_access_event.clear()
        time.sleep(0.05)


# =========================
# Utilities
# =========================
# Drain the user keypad queue to avoid stale inputs
def flush_keypad_queue():
    while not shared_keypad_queue.empty():
        try:
            shared_keypad_queue.get_nowait()
        except queue.Empty:
            break

# Blocking read from the keypad that returns None if interrupted
def get_key_input(prompt=""):
    if prompt:
        print(prompt)
    flush_keypad_queue()
    while shared_keypad_queue.empty():
        if stop_main_event.is_set() or staff_access_event.is_set():
            return None
        time.sleep(0.05)
    return shared_keypad_queue.get()

# Handle payment selection and flow: RFID (1) or PayNow QR (2)
def paymenttype():
    nextdecision = get_key_input("Pick 1 for Credit or 2 for PayNow")
    if nextdecision is None:
        return False

    if nextdecision == 1:
        return payment.payment()

    if nextdecision == 2:
        url = start_paynow_qr(port=5005)
        print("Showed QR for:", url)
        paynow_success_event.wait()
        stop_paynow_ui()
        if url:
            print("[PAYNOW] Payment success confirmed by scan.")
            return True
        print("[PAYNOW] Cancelled or interrupted.")
        return False

    if nextdecision == "*":
        return paymenttype()

    print("Invalid input")
    return False

# Append a sale record to a text logfile
def log_sale(item_name, price):
    with open("sales_log.txt", "a") as log:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log.write(f"{timestamp} - Sold: {item_name} @ ${price:.2f}\n")


# =========================
# User Mode (Main Loop)
# =========================
# Run the user-facing vending flow; exits when interrupted or finished
def main(lcd):
    global paid
    paid = False

    selection_finish_event.set()
    print("waiting")
    low_power_mode()

    while not high_power_event.is_set():
        if staff_access_event.is_set() or stop_main_event.is_set():
            return
        time.sleep(0.05)

    print("start")
    while True:
        if staff_access_event.is_set() or stop_main_event.is_set():
            print("[MAIN] Stop requested.")
            break

        for _ in range(10):
            if staff_access_event.is_set() or stop_main_event.is_set():
                break
            time.sleep(0.1)
        if staff_access_event.is_set() or stop_main_event.is_set():
            break

        while (high_power_event.is_set()
               and not staff_access_event.is_set()
               and not stop_main_event.is_set()):
            lcd.lcd_display_string("Available items:", 1)
            lcd.lcd_display_string("Scroll For Menu!", 2)
            for _ in range(15):
                if staff_access_event.is_set() or stop_main_event.is_set():
                    break
                time.sleep(0.1)
            lcd.lcd_clear()
            if staff_access_event.is_set() or stop_main_event.is_set():
                break

            selection_finish_event.clear()
            Keyvalue = get_key_input("Select a drink (1-9) or 0 to shutdown:")
            selection_finish_event.set()
            lcd.lcd_clear()

            if Keyvalue is None or staff_access_event.is_set() or stop_main_event.is_set():
                break

            if Keyvalue == 0:
                lcd.lcd_clear()
                lcd.lcd_display_string("Shutting down...", 1)
                time.sleep(0.6)
                request_low_power_with_guard(guard_sec=1.2)
                break

            if Keyvalue not in Vending_Drinks:
                print("Invalid selection.")
                continue

            item_info = Vending_Drinks[Keyvalue]
            item_name = item_info["name"]
            price = item_info["price"]
            stock = item_info["stock"]

            if stock <= 0:
                print(f"Sorry, {item_name} is out of stock.")
                lcd.lcd_display_string("Out of stock!", 1)
                time.sleep(2)
                lcd.lcd_clear()
                continue

            print(f"You selected {item_name} - ${price:.2f}")
            print("Continue?\n# - Yes | * - No | 0 - Shutdown")
            decision = get_key_input("Your choice:")

            if decision is None or staff_access_event.is_set() or stop_main_event.is_set():
                break

            if decision == "*":
                continue
            elif decision == "#":
                paid = paymenttype()
                if not paid:
                    print("Payment failed or cancelled.")
                    continue

                print("Payment successful! Dispensing drink...")
                motor_spin()
                if update_stock_in_db(Keyvalue):
                    print("Stock updated successfully.")
                    Vending_Drinks[Keyvalue]["stock"] -= 1
                    log_sale(item_name, price)
                else:
                    print("Out of stock or DB update failed.")
                lcd.lcd_display_string("Thank you!", 1)
                time.sleep(2)
                break
            elif decision == 0:
                lcd.lcd_display_string("Shutting down...", 1)
                time.sleep(0.6)
                request_low_power_with_guard(guard_sec=1.2)
                break
            else:
                print("Invalid option. Back to menu.")

        if paid:
            print("Drink dispensed. Exiting...")
            paid_event.set()
            break

    print("System idle")


# =========================
# Controller
# =========================
# Manage transitions between user mode and admin mode
def controller(lcd):
    current_mode = None
    while True:
        if staff_access_event.is_set():
            if current_mode != "admin":
                print("[MODE] Switching to ADMIN")
                stop_main_event.set()
                flush_keypad_queue()
                current_mode = "admin"

                try:
                    admin.main(lcd, flush_keys=flush_keypad_queue)
                finally:
                    print("[MODE] Admin finished.")

                print("[MODE] Waiting for switch to return to USER...")
                while staff_access_event.is_set():
                    time.sleep(0.05)

                stop_main_event.clear()
                flush_keypad_queue()
                current_mode = None

        else:
            if current_mode != "user":
                print("[MODE] Starting USER main")
                current_mode = "user"
                with app.app_context():
                    main(lcd)
                print("[MODE] USER main returned")
                current_mode = None

        time.sleep(0.05)


# =========================
# Starting Point
# =========================
if __name__ == '__main__':
    lcd = start()
    try:
        request_low_power_with_guard(guard_sec=2.0)
    except Exception:
        pass

    monitor_power()

    Thread(target=keypad.get_key, daemon=True).start()
    threading.Thread(target=MenuSelection, daemon=False).start()
    threading.Thread(target=monitor_switch, daemon=True).start()
    threading.Thread(target=burglar_system.main, daemon=True).start()

    controller(lcd)

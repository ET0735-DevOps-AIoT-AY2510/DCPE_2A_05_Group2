# =========================
# Imports
# =========================
import time
import threading
from threading import Thread
import queue
import subprocess
import sys
import os
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
from hardware_payment import process_order, scan_and_get_orders
import Integrate_CleanUp
import accelerometer

import admincode as admin
from admincode import session_done


# =========================
# Config
# =========================
# Optional external scripts (set to a command list to enable)
# e.g. RUN_COLLECTION_CMD = ["python3", "/home/pi/ET0735/TitusTests/src/collection.py"]
RUN_COLLECTION_CMD = None
# e.g. RUN_GAME_CMD = ["python3", "/home/pi/ET0735/TitusTests/src/my_game.py"]
RUN_GAME_CMD = None


# =========================
# Classes
# =========================
class SafeLCD:
    # Thread-safe wrapper around the LCD HAL to serialize writes
    def __init__(self, lcd):
        self._lcd = lcd
        self._lock = threading.RLock()
    def lcd_display_string(self, s, line):
        s = str(s)[:16].ljust(16)
        with self._lock:
            self._lcd.lcd_display_string(s, line)
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
def key_dispatch(key):
    # Wake on any key except explicit shutdown '0'
    try:
        if key not in (0, '0'):
            ping_activity()
    except Exception:
        pass
    # Route to admin while in admin session
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
def start():
    # Initialize HALs, create/attach shared LCD, and return a SafeLCD
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
def monitor_switch():
    # Poll the admin/user switch and toggle mode flags accordingly
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
def flush_keypad_queue():
    # Drain the user keypad queue to avoid stale inputs
    while not shared_keypad_queue.empty():
        try:
            shared_keypad_queue.get_nowait()
        except queue.Empty:
            break

def get_key_input(prompt=""):
    # Blocking read from keypad; returns None if interrupted/slept
    if prompt:
        print(prompt)
    flush_keypad_queue()
    while shared_keypad_queue.empty():
        if (stop_main_event.is_set()
            or staff_access_event.is_set()
            or low_power_event.is_set()):
            return None
        time.sleep(0.05)
    return shared_keypad_queue.get()

def paymenttype():
    # Handle payment selection and flow: RFID (1) or PayNow QR (2)
    nextdecision = get_key_input("Pick 1 for Credit or 2 for PayNow")
    if nextdecision is None:
        return False
    if nextdecision == 1:
        lcd.lcd_display_string("Credit selected", 2)
        return payment.payment()
    if nextdecision == 2:
        lcd.lcd_display_string("Paynow selected", 2)
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

def log_sale(item_name, price):
    # Append a sale record to a logfile
    with open("sales_log.txt", "a") as log:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log.write(f"{timestamp} - Sold: {item_name} @ ${price:.2f}\n")


# =========================
# Pre-Menu: Mode Selection
# =========================
def select_mode_menu(lcd):
    # Choose Buy(1) or Collect(2); '#' confirms; '*' resets selection
    selection = None
    while True:
        line1 = "1:Buy 2:Collect"
        line2 = "Pick 1/2  #OK"
        if selection == 1:
            line2 = "Chosen: Buy   #"
        elif selection == 2:
            line2 = "Chosen: Collect#"
        lcd.lcd_display_string(line1, 1)
        lcd.lcd_display_string(line2, 2)
        key = get_key_input("Mode? 1=Buy, 2=Collect, #=confirm, *=reset")
        if key is None or staff_access_event.is_set() or stop_main_event.is_set():
            return None, None
        if key == "*":
            selection = None
            continue
        if key in (1, 2):
            selection = int(key)
            continue
        if key == "#":
            if selection == 1:
                return "buy" , None
            if selection == 2:
                website_order = scan_and_get_orders()
                return "collect", website_order
        # ignore anything else and loop


# =========================
# Collection Flow
# =========================
def run_collection_flow(lcd, website_order):
    # Run collection workflow; when done, return to caller
    lcd.lcd_clear()
    lcd.lcd_display_string("Collection mode", 1)
    lcd.lcd_display_string("Please wait...", 2)
    try:
        process_order(website_order)
        motor_spin()
    finally:
        time.sleep(1)


# =========================
# Post-Vend: Game Prompt + Flow
# =========================
def ask_play_game_menu(lcd):
    # Ask: 1=Yes, 2=No, '#'=confirm, '*': re-pick, '0': shutdown -> low power
    selection = None
    while True:
        lcd.lcd_display_string("Play a game?", 1)
        line2 = "1:Yes 2:No  #OK"
        if selection == 1:
            line2 = "Chosen: Yes   #"
        elif selection == 2:
            line2 = "Chosen: No    #"
        lcd.lcd_display_string(line2, 2)

        key = get_key_input("Play game? 1/2, #=confirm, *=re-pick, 0=shutdown")
        if key is None or staff_access_event.is_set() or stop_main_event.is_set():
            return None

        if key == "*":
            selection = None
            continue

        if key in (1, 2):
            selection = int(key)
            continue

        if key == "#":
            if selection == 1:
                return True
            if selection == 2:
                return False
        # otherwise loop again


def run_game_flow(lcd):
    # Launch external game script if configured, else show a small placeholder
    lcd.lcd_clear()
    lcd.lcd_display_string("Starting game...", 1)
    try:
        if RUN_GAME_CMD:
            subprocess.run(RUN_GAME_CMD, check=False)
        else:
            from mathquiz import run_math_game
            result = run_math_game(lcd, get_key_input, rounds=5)
    finally:
        lcd.lcd_clear()
        time.sleep(1)


# =========================
# User Mode (Main Loop)
# =========================
def main(lcd):

    while True:
        # --- Sleep until something wakes us (ultrasonic or keypad) ---
        low_power_mode()
        while not high_power_event.is_set():
            if staff_access_event.is_set() or stop_main_event.is_set():
                return
            time.sleep(0.05)

        # Woke up -> new session state
        selection_finish_event.set()
        flush_keypad_queue()

        # --- Pre-menu: Buy / Collect / Reset ---
        mode_pick, website_order = select_mode_menu(lcd)
        lcd.lcd_clear()

        if mode_pick is None or staff_access_event.is_set() or stop_main_event.is_set():
            return

        if mode_pick == "reset":
            request_low_power_with_guard(guard_sec=1.2)
            continue

        if mode_pick == "collect":
            run_collection_flow(lcd, website_order)
            request_low_power_with_guard(guard_sec=1.2)
            continue

        # ---------------- BUY FLOW ----------------
        paid = False
        while (high_power_event.is_set()
               and not staff_access_event.is_set()
               and not stop_main_event.is_set()):
            if low_power_event.is_set():
                break

            lcd.lcd_display_string("Available items:", 1)
            lcd.lcd_display_string("Scroll For Menu!", 2)
            for _ in range(15):
                if (staff_access_event.is_set()
                    or stop_main_event.is_set()
                    or low_power_event.is_set()):
                    break
                time.sleep(0.1)
            lcd.lcd_clear()
            if (staff_access_event.is_set()
                or stop_main_event.is_set()
                or low_power_event.is_set()):
                break

            selection_finish_event.clear()
            Keyvalue = get_key_input("Select a drink (1-9) or 0 to shutdown:")
            selection_finish_event.set()
            lcd.lcd_clear()

            if Keyvalue is None or low_power_event.is_set():
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

            item = Vending_Drinks[Keyvalue]
            item_name = item["name"]; price = item["price"]; stock = item["stock"]

            if stock <= 0:
                print(f"Sorry, {item_name} is out of stock.")
                lcd.lcd_display_string("Out of stock!", 1)
                time.sleep(2)
                lcd.lcd_clear()
                continue

            print(f"You selected {item_name} - ${price:.2f}")
            print("Continue?  #=Yes  *=No  0=Shutdown")
            lcd.lcd_display_string(f"Selected: {item_name}",1)
            lcd.lcd_display_string(f"Price: {price:.2f} #Yes*No", 2)
            decision = get_key_input("Your choice:")

            if decision is None or low_power_event.is_set():
                break
            if decision == "*":
                continue
            if decision == 0:
                lcd.lcd_display_string("Shutting down...", 1)
                time.sleep(0.6)
                request_low_power_with_guard(guard_sec=1.2)
                break
            if decision == "#":
                lcd.lcd_clear()
                lcd.lcd_display_string("Payment Type",1)
                lcd.lcd_display_string("1: Credit 2: Paynow", 2)
                time.sleep(1)
                paid = paymenttype()
                if not paid:
                    print("Payment failed or cancelled.")
                    continue

                print("Payment successful! Dispensing drink...")
                lcd.lcd_display_string(f"Dispensing", 1)
                lcd.lcd_display_string(f"1 {item_name}", 2)
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

        # If we fell asleep, restart session
        if low_power_event.is_set():
            continue

        # --- Post-vend: offer a game, then sleep & restart ---
        if paid:
            from PotentialMeter import paid_event as _paid_ev
            _paid_ev.set()

            play = ask_play_game_menu(lcd)
            if play is None:
                # Interrupted by admin/sleep; just end session
                return
            if play is True:
                run_game_flow(lcd)  # run external game or placeholder

            request_low_power_with_guard(guard_sec=1.2)
            continue

        # Otherwise return to controller (e.g., admin switched)
        print("System idle")
        return


# =========================
# Controller
# =========================
def controller(lcd):
    # Manage transitions between user mode and admin mode
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
    threading.Thread(target=accelerometer.main, daemon= True).start()
    threading.Thread(target=Integrate_CleanUp.main, daemon=False).start()
    controller(lcd)

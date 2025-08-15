# main.py

# Services
import time
import threading
from threading import Thread
import queue
from datetime import datetime

from database.seed_data import app
from hal import hal_keypad as keypad
from hal import hal_lcd as LCD
from hal import hal_input_switch as switch
from power_mode import low_power_event, low_power_mode, high_power_event, staff_access_event, monitor_power
import RFID as payment
import monitor_door_status as burglar_system
from PotentialMeter import MenuSelection, selection_finish_event, paid_event
from database.db_utils import load_products_from_db, update_stock_in_db

# Admin module (receives keys via dispatcher; exports session_done)
import admincode as admin
from admincode import session_done

# ---------------------------------------------------------------------
# Thread-safe LCD wrapper (prevents interleaved writes from multiple threads)
# ---------------------------------------------------------------------
class SafeLCD:
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

# ---------------------------------------------------------------------
# Globals / State
# ---------------------------------------------------------------------
Vending_Drinks = load_products_from_db()
shared_keypad_queue = queue.Queue()
stop_main_event = threading.Event()  # ask main() to stop immediately

# ---------------------------------------------------------------------
# Keypad callback: single dispatcher for BOTH modes
# ---------------------------------------------------------------------
def key_dispatch(key):
    # While in ADMIN and session not done, deliver keys directly to admin
    if staff_access_event.is_set() and not session_done.is_set():
        try:
            admin.on_key_press(key)
        except Exception as e:
            print(f"[KEY DISPATCH] admin handler error: {e}")
        return
    # Otherwise, normal vending input
    shared_keypad_queue.put(key)

# ---------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------
def start():
    keypad.init(key_dispatch)                   # HAL scanner calls dispatcher
    switch.init()
    Thread(target=keypad.get_key, daemon=True).start()
    real_lcd = LCD.lcd()
    lcd = SafeLCD(real_lcd)                     # shared, thread-safe LCD
    lcd.lcd_clear()
    return lcd

# ---------------------------------------------------------------------
# Switch monitor
# ---------------------------------------------------------------------
def monitor_switch():
    while True:
        input_val = switch.read_slide_switch()
        if input_val == 0:  # Admin mode
            if not staff_access_event.is_set():
                print("[SWITCH] Admin mode ON")
                staff_access_event.set()
                stop_main_event.set()  # stop vending ASAP
        else:
            # Only leave admin after the admin session finishes
            if staff_access_event.is_set() and session_done.is_set():
                print("[SWITCH] Admin mode OFF")
                staff_access_event.clear()
        time.sleep(0.05)

# ---------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------
def flush_keypad_queue():
    while not shared_keypad_queue.empty():
        try:
            shared_keypad_queue.get_nowait()
        except queue.Empty:
            break

def get_key_input(prompt=""):
    """Blocking read from keypad, but aborts early if switching to Admin."""
    if prompt:
        print(prompt)
    flush_keypad_queue()
    while shared_keypad_queue.empty():
        if stop_main_event.is_set() or staff_access_event.is_set():
            return None  # interrupted by Admin switch
        time.sleep(0.05)
    return shared_keypad_queue.get()

def paymenttype():
    """Returns True on successful payment, False otherwise. Interruptible."""
    nextdecision = get_key_input("Pick 1 for Credit or 2 for PayNow")
    if nextdecision is None:
        return False
    if nextdecision == 1:
        return payment.payment()
    elif nextdecision == 2:
        print("QR generating (simulated)")
        time.sleep(1)
        return True
    elif nextdecision == "*":
        return paymenttype()
    else:
        print("Invalid input")
        return False

def log_sale(item_name, price):
    with open("sales_log.txt", "a") as log:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log.write(f"{timestamp} - Sold: {item_name} @ ${price:.2f}\n")

# ---------------------------------------------------------------------
# Vending main loop (User mode)
# ---------------------------------------------------------------------
def main(lcd):
    global paid
    paid = False

    selection_finish_event.set()
    print("waiting")
    low_power_mode()

    # Wait for high power, but allow interruption by Admin
    while not high_power_event.is_set():
        if staff_access_event.is_set() or stop_main_event.is_set():
            return
        time.sleep(0.05)

    print("start")
    while True:
        # Exit immediately if Admin requests stop
        if staff_access_event.is_set() or stop_main_event.is_set():
            print("[MAIN] Stop requested.")
            break

        # Small sleep but remain interruptible
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
            for _ in range(15):  # ~1.5s but interruptible
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

            # If interrupted during input, stop immediately
            if Keyvalue is None or staff_access_event.is_set() or stop_main_event.is_set():
                break

            if Keyvalue == 0:
                lcd.lcd_clear()
                lcd.lcd_display_string("Shutting down...", 1)
                time.sleep(1.5)
                low_power_mode()
                lcd.lcd_clear()
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
                time.sleep(1.5)
                low_power_mode()
                lcd.lcd_clear()
                break
            else:
                print("Invalid option. Back to menu.")

        if paid:
            print("Drink dispensed. Exiting...")
            paid_event.set()
            break

    print("System idle")
    
def controller(lcd):
    current_mode = None
    while True:
        if staff_access_event.is_set():
            if current_mode != "admin":
                print("[MODE] Switching to ADMIN")
                stop_main_event.set()      # stop vending loop ASAP
                flush_keypad_queue()       # drop stale presses
                current_mode = "admin"

                try:
                    # Pass shared SafeLCD and the flusher (no keypad re-init)
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
                    main(lcd)  # returns when Admin flips or stop_main_event set
                print("[MODE] USER main returned")
                current_mode = None

        time.sleep(0.05)

# ---------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------
if __name__ == '__main__':
    lcd = start()
    monitor_power()
    threading.Thread(target=MenuSelection, daemon=False).start()
    threading.Thread(target=monitor_switch, daemon=True).start()
    threading.Thread(target=burglar_system.main, daemon=True).start()

    # Controller orchestrates both modes
    controller(lcd)

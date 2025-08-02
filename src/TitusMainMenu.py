# Services
import time
import threading
from threading import Thread
import queue
from hal import hal_keypad as keypad
from hal import hal_lcd as LCD
from hal import hal_input_switch as switch
from power_mode import low_power_event
from power_mode import low_power_mode
from power_mode import high_power_event
from power_mode import staff_access_event
import TitusRFID as payment
from power_mode import monitor_power
import admincode as admin
import monitor_door_status as burglar_system
from PotentialMeter import MenuSelection
from PotentialMeter import selection_finish_event
from PotentialMeter import Vending_Drinks
from PotentialMeter import paid_event

admin_thread_started = threading.Event()

# Shared queue
shared_keypad_queue = queue.Queue()

# Callback for keypad
def key_pressed(key):
    shared_keypad_queue.put(key)

# Init hardware
def start():
    keypad.init(key_pressed)
    switch.init()
    keypad_thread = Thread(target=keypad.get_key, daemon=True)
    keypad_thread.start()
    lcd = LCD.lcd()
    lcd.lcd_clear()
    return lcd

def reset():
    if low_power_event.is_set():
        print("Detected low power. Restarting the program...")
        low_power_event.clear()
        main()
        return

# Get switch input
def monitor_switch():
    while True:
        input_val = switch.read_slide_switch()
        if input_val == 0:  # Admin mode
            if not staff_access_event.is_set():
                print("[SWITCH] Admin mode ON")
                staff_access_event.set()
                if not admin_thread_started.is_set():
                    threading.Thread(target=admin.main(), args=(True,), daemon=False).start()
                    admin_thread_started.set()
        else:
            if staff_access_event.is_set():
                print("[SWITCH] Admin mode OFF")
                staff_access_event.clear()
                admin_thread_started.clear()
        time.sleep(0.2)

# Helper: Flush keypad queue
def flush_keypad_queue():
    while not shared_keypad_queue.empty():
        try:
            shared_key = shared_keypad_queue.get_nowait()
        except queue.Empty:
            break

# Helper: Get a single key input after flushing old ones
def get_key_input(prompt=""):
    if prompt:
        print(prompt)
    flush_keypad_queue()
    while shared_keypad_queue.empty():
        time.sleep(0.1)
    return shared_keypad_queue.get()

def paymenttype():
    nextdecision = get_key_input("Pick 1 for Credit or 2 for PayNow")
    if nextdecision == 1:
        paid = payment.payment()
    elif nextdecision == 2:
        print("qr generating")
    elif nextdecision == "*":
        paymenttype()
    else:
        print("invalid input")
    return paid

# Main program loop
def main():
    lcd = start()
    global paid
    paid = False
    staff_access = False
    selection_finish_event.set()
    monitor_power()
    threading.Thread(target=MenuSelection, daemon=False).start()
    #threading.Thread(target=reset, daemon=True).start()
    threading.Thread(target=monitor_switch, daemon=True).start()
    threading.Thread(target=burglar_system.main, args=(paid, staff_access), daemon=True).start()
    print("waiting")
    low_power_mode()
    high_power_event.wait()
    print("start")
    while True:
        time.sleep(1)
        while high_power_event.is_set():
            lcd.lcd_display_string("Available items:", 1)
            lcd.lcd_display_string("Scroll For Menu!", 2)
            time.sleep(1.5)
            lcd.lcd_clear()
            selection_finish_event.clear()
            Keyvalue = get_key_input("Please select a drink (1-9) or 0 to shutdown:")
            selection_finish_event.set()
            lcd.lcd_clear()
            if Keyvalue == 0:
                lcd.lcd_clear()
                lcd.lcd_display_string("Shutting down...", 1)
                low_power_mode()
                lcd.lcd_clear()
                break

            if Keyvalue not in Vending_Drinks:
                print("Invalid selection.")
                continue

            item_info = Vending_Drinks[Keyvalue]
            item_name, price = list(item_info.items())[0]

            print(f"You selected {item_name} - ${price:.2f}")
            print("Would you like to continue?")
            print("# - Continue\n* - Back\n0 - Shutdown")

            decision = get_key_input("Your choice:")
            if decision == "*":
                continue
            elif decision == "#":
                paid = paymenttype()
                if paid == False:
                    print("Invalid payment, restarting...")
                    continue
                elif paid == True:
                    print("Successful payment, please collect your drink.")
                    break
            elif decision == 0:
                lcd.lcd_clear()
                lcd.lcd_display_string("Shutting down...", 1)
                low_power_mode()
                lcd.lcd_clear()
                break
            else:
                print("Invalid option, returning to menu.")

        if paid:
            print("break cuz paid")
            paid_event.set()
            break
    print("end")

if __name__ == '__main__':
    main()
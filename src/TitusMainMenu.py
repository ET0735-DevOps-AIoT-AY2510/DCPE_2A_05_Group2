# Services
import time
import threading
from threading import Thread
import queue
from hal import hal_keypad as keypad
from hal import hal_lcd as LCD
import TitusRFID as payment
import power_mode as power

# Variables
shutdown = False

# Dictionary
Vending_Drinks = {
    "Water Bottle": 0.50,
    "Coke": 2.00,
    "Sprite": 2.00,
    "Ayataka": 1.00,
    "Milk Tea": 3.00,
    "Coffee": 3.00,
    "A&W": 2.00,
    "Red Bull": 3.00,
    "Diet Coke": 2.00
}

item_list = {
    1: "Water Bottle",
    2: "Coke",
    3: "Sprite",
    4: "Ayataka",
    5: "Milk Tea",
    6: "Coffee",
    7: "A&W",
    8: "Red Bull",
    9: "Diet Coke"
}

# Shared queue
shared_keypad_queue = queue.Queue()

# Callback for keypad
def key_pressed(key):
    shared_keypad_queue.put(key)

# Init hardware
def start():
    keypad.init(key_pressed)
    keypad_thread = Thread(target=keypad.get_key, daemon=True)
    keypad_thread.start()
    lcd = LCD.lcd()
    lcd.lcd_clear()

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

# Main program loop
def main():
    start()
    power_mode = threading.Thread(target=power, daemon=True).start()
    while True:
        while power_mode:
            print("\nAvailable items:")
            for num, item in item_list.items():
                print(f"{num}. {item} - ${Vending_Drinks[item]:.2f}")

            Keyvalue = get_key_input("Please select a drink (1-9) or 0 to shutdown:")
            if Keyvalue == 0:
                print("Shutting down...")
                break

            if Keyvalue not in item_list:
                print("Invalid selection.")
                continue

            selected_item = item_list[Keyvalue]
            print(f"You selected {selected_item} (${Vending_Drinks[selected_item]:.2f})")
            print("Would you like to continue?")
            print("# - Continue\n* - Back\n0 - Shutdown")

            decision = get_key_input("Your choice:")
            if decision == "*":
                continue
            elif decision == "#":
                paid = payment.payment()
                if paid == False:
                    print("Invalid payment, restarting...")
                    continue
                elif paid == True:
                    print("Successful payment, please collect your drink.")
                    break
            elif decision == 0:
                print("Shutting down...")
                break
            else:
                print("Invalid option, returning to menu.")
        if shutdown:
            break

if __name__ == '__main__':
    main()
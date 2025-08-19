from hal import hal_adc as potentialmeter
from hal import hal_lcd as lcd
import threading
import time
from database.db_utils import load_products_from_db, update_stock_in_db
selection_finish_event = threading.Event()
paid_event = threading.Event()
range_size = 1023 // 9

def start():
    potentialmeter.init()
    LCD = lcd.lcd()
    return LCD

def get_item_index(potential_val):
    index = potential_val // range_size + 1
    return min(index, 9)

def MenuSelection():
    LCD = start()
    last_index = -1
    time.sleep(1)
    while True:
        while not selection_finish_event.is_set():
            Vending_Drinks = load_products_from_db()
            potential_val = potentialmeter.get_adc_value(1)
            item_index = get_item_index(potential_val)
            if last_index != item_index and item_index in Vending_Drinks:
                item = Vending_Drinks[item_index]
                item_name = item["name"]
                price = item["price"]
                stock = item["stock"]

                print(f"ADC: {potential_val:4d} | Selected: {item_name} (${price:.2f})")
                LCD.lcd_clear()
                LCD.lcd_display_string(f"{item_index}: {item_name}", 1)
                LCD.lcd_display_string(f"P: ${price:.2f} S: {stock}", 2)
                time.sleep(0.5)
                last_index = item_index

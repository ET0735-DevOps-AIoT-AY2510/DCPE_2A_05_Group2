import time
from threading import Thread
from hal import hal_rfid_reader as rfid_reader
from hal import hal_lcd as LCD
reader = rfid_reader.init()
lcd = LCD.lcd()

def payment():
    print("Processing payment...")
    lcd.lcd_clear()
    paid = False
    count = 15
    while(count != 0):
        id = reader.read_id_no_block()
        id = str(id)
        print("RFID card ID = " + id)
        # Display RFID card ID on LCD line 2
        lcd.lcd_display_string(id, 2)
        time.sleep(1)
        if id != "None":
            paid = True
            break
        else:
            print(count, "secs left to pay...")
            count -= 1
    return paid
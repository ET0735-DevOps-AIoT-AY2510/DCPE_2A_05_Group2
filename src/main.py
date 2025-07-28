import time
from threading import Thread
import queue

from hal import hal_led as led
from hal import hal_lcd as LCD
from hal import hal_adc as adc
from hal import hal_buzzer as buzzer
from hal import hal_keypad as keypad
from hal import hal_moisture_sensor as moisture_sensor
from hal import hal_input_switch as input_switch
from hal import hal_ir_sensor as ir_sensor
from hal import hal_rfid_reader as rfid_reader
from hal import hal_servo as servo
from hal import hal_temp_humidity_sensor as temp_humid_sensor
from hal import hal_usonic as usonic
from hal import hal_dc_motor as dc_motor
from hal import hal_accelerometer as accel

#Empty list to store sequence of keypad presses
shared_keypad_queue = queue.Queue()




#Call back function invoked when any key on keypad is pressed
def key_pressed(key):
    shared_keypad_queue.put(key)


def monitor_door(paid, staff_access):

    while True:
        ir_value = ir_sensor.get_ir_sensor_state()
        time.sleep(2)
        print("IR Sensor State:", ir_value)
        if ir_value is False and paid is False and staff_access is False:
            buzzer.beep(0.5, 0.5, 10)
            time.sleep(2)

        

def main():
    # Initialising the Hardware components and variable
    ir_sensor.init()
    buzzer.init()
    paid = False
    staff_access = False

    # Initialising and Starting Threads
    door_thread = Thread(target=monitor_door, args=(paid, staff_access), daemon=True)
    door_thread.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Program Stopped")





if __name__ == '__main__':
    main()
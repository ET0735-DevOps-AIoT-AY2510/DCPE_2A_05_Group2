import time
from threading import Thread
import queue

from hal import hal_rfid_reader as rfid_reader
from hal import hal_ir_sensor as ir_sensor
from hal import hal_buzzer as buzzer
from hal import hal_input_switch as switch


def monitor_door(paid, staff_access):

    while True:
        ir_value = ir_sensor.get_ir_sensor_state()
        time.sleep(2)
        print("IR Sensor State:", ir_value)
        if ir_value is False and paid is False and staff_access is False:
            buzzer.beep(0.5, 0.5, 10)
            time.sleep(2)

def inputswitch():
    switch.init()

def main():
    # Initialising the Hardware components and variable
    ir_sensor.init()
    buzzer.init()
    paid = False
    staff_access = False
    # Initialising and Starting Threads
    door_thread = Thread(target=monitor_door, args=(paid, staff_access), daemon=True).start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Program Stopped")



    

if __name__ == '__main__':
    main()
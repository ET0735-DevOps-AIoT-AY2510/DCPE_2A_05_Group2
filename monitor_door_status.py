import time
import threading
import queue

from hal import hal_ir_sensor as ir_sensor
from hal import hal_buzzer as buzzer
from hal import hal_input_switch as switch

from power_mode import staff_access_event as staff_access
from Integrate_CleanUp import burglar_detect
from PotentialMeter import paid_event as paid



def monitor_door():

    while True:
        if not staff_access.is_set():
            ir_value = ir_sensor.get_ir_sensor_state()
            time.sleep(1)
            print("IR Sensor State:", ir_value)
            if ir_value == True:
                print("Burglar Detected!")
                buzzer.beep(0.5, 0.5, 1)
                burglar_detect.set()
                time.sleep(1)

def main():
    # Initialising the Hardware components and variable
    ir_sensor.init()
    buzzer.init()
    # Initialising and Starting Threads
    threading.Thread(target=monitor_door, daemon=True).start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Program Stopped")
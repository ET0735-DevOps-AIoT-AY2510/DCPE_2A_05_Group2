from hal import hal_dc_motor as motor
import time

def motor_spin():
    motor.set_motor_speed(50)  # Turn motor on
    time.sleep(3)  # Wait for 5 seconds
    motor.set_motor_speed(0)  # Turn motor off

def main():
    motor_spin()

if __name__ == '__main__':
    main()
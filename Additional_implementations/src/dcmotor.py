from hal import hal_dc_motor as motor
import RPi.GPIO as GPIO
import time

def motor_spin():
    motor.init()
    GPIO.output(23, GPIO.HIGH)  # Turn motor on
    time.sleep(5)  # Wait for 5 seconds
    GPIO.output(23, GPIO.LOW)  # Turn motor off

def main():
    motor_spin()

if __name__ == '__main__':
    main()
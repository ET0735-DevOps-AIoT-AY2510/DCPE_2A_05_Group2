import RPi.GPIO as GPIO
import time
from hal import hal_usonic as usonic
from hal import hal_lcd as lcd
from hal import hal_keypad as keypad
# Function to measure the distance
usonic.init()
lcd_instance = lcd.lcd()  # Initialize the LCD instance

def display_dist():
    Distance = usonic.get_distance()
    print(f"Distance: {Distance} cm")
    return Distance

def high_power_mode():
    # Turn on the display and backlight (Command for turning the display on)
    lcd_instance.backlight(1)
    print("High Power Mode: Backlight ON")

def low_power_mode():
    # Turn off the display and backlight (Command for turning the display off)
    lcd_instance.backlight(0)
    print("Low Power Mode: Backlight OFF")

def main():
    while True:  # Infinite loop to continuously measure distance
        Distance = display_dist()
        time.sleep(1)  # Get the distance measurement
        if Distance >= 10:
            time.sleep(1)
            low_power_mode()  # Turn off backlight when distance is >= 10 cm
        else:
            time.sleep(1)
            high_power_mode()  # Turn on backlight when distance is < 10 cm

if __name__ == '__main__':
    main()
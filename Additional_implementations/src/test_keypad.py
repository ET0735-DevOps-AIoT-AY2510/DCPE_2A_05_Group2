import time
import RPi.GPIO as GPIO
from hal import hal_keypad as keypad
from hal import hal_lcd as lcd
import threading

lcd_instance = lcd.lcd()  # Initialize the LCD instance

# Global variable to track the last keypress time
last_keypress_time = time.time()

# Set the timeout for 5 seconds
INACTIVITY_TIMEOUT = 5


def high_power_mode():
    # Turn on the display and backlight (Command for turning the display on)
    lcd_instance.backlight(1)  # Turn the backlight on
   
    print("High Power Mode: Backlight ON")

def low_power_mode():
    # Turn off the display and backlight (Command for turning the display off)
    lcd_instance.backlight(0)  # Turn the backlight off

    print("Low Power Mode: Backlight OFF")

# Define the callback function to handle key press events
def key_press_callback(key):
    global last_keypress_time
    last_keypress_time = time.time()  # Update the last key press time
    high_power_mode()  # Turn on the backlight when a key is pressed
    print(f"Button pressed")

def monitor_inactivity():
    """Monitor inactivity timeout and turn off the backlight after 5 seconds of inactivity."""
    global last_keypress_time
    while True:
        current_time = time.time()

        # Check if 5 seconds have passed since the last key press
        if current_time - last_keypress_time >= INACTIVITY_TIMEOUT:
            low_power_mode()  # Turn off the backlight after 5 seconds of inactivity

        time.sleep(1)  # Sleep for a short time to reduce CPU usage

def detect_keypress():
    """Detect key presses and invoke the callback."""
    keypad.init(key_press_callback)

    print("Press any button on the keypad...")

    while True:
        keypad.get_key()  # Detect key presses and call the callback function
        time.sleep(0.1)  # Small delay to avoid excessive CPU usage

def main():
        # Start the inactivity monitor thread
    inactivity_thread = threading.Thread(target=monitor_inactivity)
    inactivity_thread.daemon = True  # Allow the thread to exit when the main program ends
    inactivity_thread.start()

    # Start the keypad detection thread
    keypad_thread = threading.Thread(target=detect_keypress)
    keypad_thread.daemon = True  # Allow the thread to exit when the main program ends
    keypad_thread.start()
    # Initialize the keypad and pass the callback function
    keypad.init(key_press_callback)

    print("Press any button on the keypad...")

    try:
        while True:
            current_time = time.time()
            
            # Check if 5 seconds have passed since the last key press
            if current_time - last_keypress_time > INACTIVITY_TIMEOUT:
                low_power_mode()  # Turn off the backlight after 5 seconds of inactivity

            else:
                high_power_mode()

    except KeyboardInterrupt:
        print("Exiting program...")
        GPIO.cleanup()  # Clean up GPIO when exiting

if __name__ == '__main__':
    main()
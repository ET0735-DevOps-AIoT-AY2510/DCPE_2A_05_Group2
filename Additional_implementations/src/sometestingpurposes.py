import time
from hal import hal_lcd as LCD

# Instantiate the LCD
lcd = LCD.lcd()

def adjust_backlight():
    """Continuously adjust the LCD backlight from dim to bright and back."""
    # Set the backlight to initial state (dim)
    lcd.backlight(0)  # Start with the backlight off

    while True:
        # Gradually brighten the backlight
        for i in range(0, 101, 5):  # Increase brightness from 0% to 100% in steps of 5
            lcd.backlight(i)  # Adjust backlight brightness (0 - 100)
            time.sleep(0.1)  # Wait for a short time to create a smooth transition

        # Gradually dim the backlight
        for i in range(100, -1, -5):  # Decrease brightness from 100% to 0% in steps of 5
            lcd.backlight(i)  # Adjust backlight brightness (100 - 0)
            time.sleep(0.1)  # Wait for a short time to create a smooth transition

if __name__ == '__main__':
    adjust_backlight()

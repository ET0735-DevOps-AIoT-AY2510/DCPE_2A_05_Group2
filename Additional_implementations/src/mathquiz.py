import random
import time
import threading
from hal import hal_lcd as LCD
from hal import hal_keypad as keypad
import RPi.GPIO as GPIO
import dcmotor

# Global variables
user_input = ""
correct_answer = 0
correct_attempts = 0  # Tracks correct answers
attempts = 0  # Tracks the number of attempts
lcd = LCD.lcd()

# Debounce variables
last_key_time = 0
debounce_delay = 0.1  # 100 milliseconds

# Function to keep the backlight on
def keep_backlight_on():
    while True:
        lcd.backlight(1)  # Keep the backlight on
        time.sleep(1)  # Sleep for a while to avoid busy waiting

# Math question generation
def generate_question():
    operations = ['+', '-', '*']  # Removed division to ensure integer answers
    num1 = random.randint(1, 10)
    num2 = random.randint(1, 10)
    operation = random.choice(operations)

    # Ensure positive integer answers
    if operation == '-':
        # Ensure num1 is greater than num2 for subtraction
        if num1 < num2:
            num1, num2 = num2, num1

    question = f"{num1} {operation} {num2} = ?"
    correct_answer = eval(f"{num1} {operation} {num2}")
    
    return question, correct_answer

# Handle key press callback
def key_press_cbk(key):
    global user_input, correct_answer, last_key_time, attempts, correct_attempts
    current_time = time.time()

    # Debounce logic
    if current_time - last_key_time < debounce_delay:
        return  # Ignore this key press due to debounce
    last_key_time = current_time

    if key == '#':  # Enter key
        try:
            # Check if the input is a valid positive integer
            if user_input.isdigit() and int(user_input) > 0:
                if int(user_input) == correct_answer:  # Compare as integers
                    lcd.lcd_clear()
                    lcd.lcd_display_string("Correct!", line=1)  # Display result on line 2
                    correct_attempts += 1  # Increment correct attempts
                else:
                    lcd.lcd_clear()  # Clear the LCD
                    lcd.lcd_display_string(f"Wrong!", line=1)  # Display result on line 2
                    time.sleep(1.5)
                    lcd.lcd_clear()
                    lcd.lcd_display_string("TRY AGAIN ", line=1)
                    lcd.lcd_display_string("NEXT TIME!", line=2)  # Display "NICE TRY!"
                    time.sleep(3)
                    lcd.lcd_clear()  # Clear the LCD
                    return  # Do not continue to the next question
            # Increment attempts count
            attempts += 1

            # Check if we've reached 5 attempts
            if attempts == 10:
                if correct_attempts == 10:
                    lcd.lcd_clear()
                    lcd.lcd_display_string("CONGRATS ON", line=1)
                    lcd.lcd_display_string("FREE DRINK!", line=2)
                    dcmotor.motor_spin()
                    time.sleep(3)
                    lcd.lcd_clear()
                    lcd.lcd_display_string("End of Game", line=1)
                    time.sleep(3)
                    lcd.lcd_clear()

                else:
                    lcd.lcd_clear()
                    lcd.lcd_display_string(f"Wrong!", line=1)  # Display result on line 2
                    time.sleep(1)  # Pause to show the wrong answer
                    lcd.lcd_clear()  # Clear the display
                    lcd.lcd_display_string("TRY AGAIN ", line=1)
                    lcd.lcd_display_string("NEXT TIME!", line=2)  # Display "NICE TRY!"
                    time.sleep(2)  # Show the message for a short time
                # End the program immediately
                time.sleep(1)
                lcd.lcd_clear()
                

            time.sleep(2)  # Brief pause to show the result
            ask_question()  # Get the next question

        except ValueError:
            lcd.lcd_display_string("Invalid input!", line=2)  # Display error on line 2
            time.sleep(2)
            ask_question()  # Get the next question

    elif key == '':  # Handle the '' key to delete a character (backspace)
        if user_input:  # Only delete if there's something to delete
            user_input = user_input[:-1]  # Remove the last character
            lcd.lcd_clear()  # Clear the LCD before updating it
            lcd.lcd_display_string(user_input, line=2)  # Update input display on line 2
        lcd.backlight(1)  # Ensure backlight stays on

    else:  # Update the answer with the key pressed
        user_input += str(key)
        lcd.lcd_clear()  # Clear the LCD before showing updated input
        lcd.lcd_display_string(user_input, line=2)  # Update input display on line 2
        lcd.backlight(1)  # Ensure backlight stays on

# Ask the question
def ask_question():
    global correct_answer, user_input
    user_input = ""
    question, correct_answer = generate_question()
    lcd.lcd_clear()  # Clear the display to refresh
    lcd.lcd_display_string(question, line=1)  # Display question on line 1 (always visible)
    lcd.lcd_display_string(user_input, line=2)  # Display user input on line 2 (updates with each key press)
    keypad.get_key()  # Wait for keypress

# Function to run the keypad in a separate thread
def keypad_thread():
    while True:
        keypad.get_key()  # Continuously listen for key presses

# Initialize the keypad
keypad.init(key_press_cbk)  # Initialize the keypad

# Start the backlight thread
backlight_thread = threading.Thread(target=keep_backlight_on, daemon=True)
backlight_thread.start()

# Start the keypad listener thread
keypad_thread = threading.Thread(target=keypad_thread, daemon=True)
keypad_thread.start()

# Start the quiz
def main():
    ask_question()

if __name__ == '__main__':
    main()
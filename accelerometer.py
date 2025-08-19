import time
import math
from hal import hal_accelerometer as accel
from hal import hal_buzzer as buzzer
from Integrate_CleanUp import burglar_detect
# Initialize accelerometer and buzzer
accel_device = accel.init()
buzzer.init()

# Function to detect rapid movement
def detect_rapid_movement():
    # Get the raw x, y, z values from the accelerometer
    x, y, z = accel_device.get_3_axis()

    # Calculate the magnitude of the movement (vector length)
    magnitude = math.sqrt(x*2 + y*2 + z*2)
    
    # Define a threshold for rapid movement (this value may need tweaking)
    threshold = 1.5  # Adjust this value based on your needs
    
    # If the magnitude exceeds the threshold, it's considered rapid movement
    if magnitude > threshold:
        return True
    return False

# Main loop to check for rapid movement and trigger the buzzer
def main():
    try:
        while True:
            if detect_rapid_movement():
                print("Rapid movement detected! Buzzing...")
                buzzer.turn_on_with_timer(1)  # Buzz for 1 second
                burglar_detect.set()
            time.sleep(0.1)  # Sleep for 100ms before the next reading

    except KeyboardInterrupt:
        print("Program terminated.")
        buzzer.turn_off()  # Turn off buzzer when the program is terminated

if __name__ == "__main__":
    main()

import RPi.GPIO as GPIO
from unittest import mock
from dcmotor import motor_spin  # Replace with the correct import path


def test_motor_spin():
    # Mock the motor initialization, GPIO output, and time.sleep
    with mock.patch('hal.hal_dc_motor.init') as mock_motor_init, \
         mock.patch('RPi.GPIO.output') as mock_gpio_output, \
         mock.patch('time.sleep') as mock_sleep:

        # Act: Call the motor_spin function
        motor_spin()

        # Assert motor initialization was called
        assert mock_motor_init.call_count == 1, "motor.init() should be called once"

        # Assert that GPIO.output(23, GPIO.HIGH) is called (motor on)
        mock_gpio_output.assert_any_call(23, mock.ANY)
        assert (23, GPIO.HIGH) in [args for args, _ in mock_gpio_output.call_args_list], "GPIO.output(23, GPIO.HIGH) should be called"

        # Assert that GPIO.output(23, GPIO.LOW) is called (motor off)
        assert (23, GPIO.LOW) in [args for args, _ in mock_gpio_output.call_args_list], "GPIO.output(23, GPIO.LOW) should be called"

        # Assert time.sleep(5) was called to simulate the 5-second motor run
        mock_sleep.assert_called_with(5), "time.sleep(5) should be called"


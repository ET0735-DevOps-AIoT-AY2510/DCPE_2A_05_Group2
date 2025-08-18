from unittest.mock import MagicMock, patch
import time
import pytest
from power_mode import high_power_mode, lcd_instance
from power_mode import low_power_mode, low_power_event, high_power_event, selection_finish_event
from power_mode import monitor_ultrasonic, high_power_mode, staff_access_event, ULTRASONIC_RANGE

def test_high_power_mode():
    with patch('power_mode.lcd_instance', new_callable=MagicMock) as mock_lcd:
        mock_lcd.backlight = MagicMock()
        low_power_event.clear()
        high_power_event.clear()
        high_power_mode()
        mock_lcd.backlight.assert_called_once_with(1)
        assert high_power_event.is_set() == True
        assert low_power_event.is_set() == False

def test_low_power_mode():
    with patch('power_mode.lcd_instance', new_callable=MagicMock) as mock_lcd:
        mock_lcd.lcd_clear = MagicMock()
        mock_lcd.backlight = MagicMock()
        low_power_event.clear()
        high_power_event.clear()
        with patch('power_mode.selection_finish_event.set') as mock_finish_event:
            low_power_mode()
            mock_lcd.lcd_clear.assert_called_once()
            mock_lcd.backlight.assert_called_once_with(0)
            assert high_power_event.is_set() == False
            assert low_power_event.is_set() == True
            mock_finish_event.assert_called_once()

def test_monitor_ultrasonic():
    with patch('power_mode.high_power_mode') as mock_high_power_mode:
        with patch('power_mode.usonic.get_distance') as mock_get_distance:
            mock_get_distance.return_value = 15
            start_time = time.time()
            while time.time() - start_time < 5:  # Run for 5 seconds
                monitor_ultrasonic()
            mock_high_power_mode.assert_not_called()
            mock_get_distance.return_value = 5
            start_time = time.time()
            while time.time() - start_time < 5:  # Run for 5 seconds
                monitor_ultrasonic()
            mock_high_power_mode.assert_called_once()
            assert high_power_event.is_set() == True
            assert low_power_event.is_set() == False

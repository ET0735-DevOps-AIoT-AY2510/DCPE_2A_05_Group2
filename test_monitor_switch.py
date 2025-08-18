import pytest
from unittest.mock import patch, MagicMock
import time
import threading
from MainMenu import staff_access_event, stop_main_event, session_done
from hal import hal_input_switch as switch  # Importing the switch module which is being used in monitor_switch
from MainMenu import monitor_switch  # Replace with actual file name

# =========================
# Mock Setup for Test
# =========================
@pytest.fixture
def mock_setup():
    # Mocking the switch module and events
    with patch.object(switch, "read_slide_switch") as mock_switch:
        with patch.object(staff_access_event, "set") as mock_staff_set:
            with patch.object(staff_access_event, "clear") as mock_staff_clear:
                with patch.object(stop_main_event, "set") as mock_stop_main_set:
                    with patch.object(stop_main_event, "clear") as mock_stop_main_clear:
                        with patch.object(session_done, "is_set", return_value=True) as mock_session_done:
                            # Return mocked objects for use in test
                            yield mock_switch, mock_staff_set, mock_staff_clear, mock_stop_main_set, mock_stop_main_clear, mock_session_done

# =========================
# Test: Monitor Switch ON (Admin Mode)
# =========================
def test_monitor_switch_on(mock_setup):
    mock_switch, mock_staff_set, mock_staff_clear, mock_stop_main_set, mock_stop_main_clear, mock_session_done = mock_setup

    # Simulate the switch being off (input_val == 0)
    mock_switch.return_value = 0

    # Run monitor_switch in a separate thread
    thread = threading.Thread(target=monitor_switch, daemon=True)
    thread.start()

    # Allow the function to run for a short time
    time.sleep(0.1)

    # Assert that staff_access_event.set() and stop_main_event.set() were called when switch is off
    assert mock_staff_set.called, "staff_access_event.set() was not called"
    assert mock_stop_main_set.called, "stop_main_event.set() was not called"

    # Stop the loop using the event
    stop_main_event.set()

    # Ensure that the thread stops
    thread.join()


# =========================
# Test: Monitor Switch OFF (Admin Mode Off)
# =========================
def test_monitor_switch_off(mock_setup):
    mock_switch, mock_staff_set, mock_staff_clear, mock_stop_main_set, mock_stop_main_clear, mock_session_done = mock_setup

    # Simulate the switch being on (input_val != 0)
    mock_switch.return_value = 1

    # Run monitor_switch in a separate thread
    thread = threading.Thread(target=monitor_switch, daemon=True)
    thread.start()

    # Allow the function to run for a short time
    time.sleep(0.1)

    # Simulate session_done being set, which triggers staff_access_event.clear()
    mock_session_done.return_value = True
    mock_switch.return_value = 1  # Keep the switch on

    # Assert that staff_access_event.clear() was called
    assert mock_staff_clear.called, "staff_access_event.clear() was not called"

    # Stop the loop using the event
    stop_main_event.set()

    # Ensure that the thread stops
    thread.join()

import pytest
from unittest.mock import patch, MagicMock
from MainMenu import paymenttype  # Replace with actual file name


# =========================
# Mock Setup for Test
# =========================
@pytest.fixture
def mock_setup():
    # Mocking get_key_input function
    with patch('MainMenu.get_key_input') as mock_get_key_input:
        # Mocking payment.payment and related functions
        with patch('MainMenu.payment.payment') as mock_payment:
            with patch('MainMenu.start_paynow_qr') as mock_start_paynow_qr:
                with patch('MainMenu.paynow_success_event.wait') as mock_paynow_wait:
                    with patch('MainMenu.stop_paynow_ui') as mock_stop_paynow_ui:
                        # Return mocked objects for use in test
                        yield mock_get_key_input, mock_payment, mock_start_paynow_qr, mock_paynow_wait, mock_stop_paynow_ui


# =========================
# Test: Successful RFID Payment
# =========================
def test_paymenttype_credit(mock_setup):
    # Unpack the mocked objects
    mock_get_key_input, mock_payment, mock_start_paynow_qr, mock_paynow_wait, mock_stop_paynow_ui = mock_setup

    # Simulate the user pressing '1' for RFID (Credit)
    mock_get_key_input.return_value = 1

    # Simulate a successful payment process
    mock_payment.return_value = True

    # Call the paymenttype function
    result = paymenttype()

    # Assert that the payment function was called
    mock_payment.assert_called_once()
    assert result is True, "Payment was not successful"


# =========================
# Test: Successful PayNow QR Payment
# =========================
def test_paymenttype_paynow(mock_setup):
    # Unpack the mocked objects
    mock_get_key_input, mock_payment, mock_start_paynow_qr, mock_paynow_wait, mock_stop_paynow_ui = mock_setup

    # Simulate the user pressing '2' for PayNow
    mock_get_key_input.return_value = 2

    # Simulate PayNow QR generation and success event wait
    mock_start_paynow_qr.return_value = "http://example.com/qr"
    mock_paynow_wait.return_value = None  # Simulate success after waiting

    # Call the paymenttype function
    result = paymenttype()

    # Assert that PayNow QR was started and success event was waited for
    mock_start_paynow_qr.assert_called_once_with(port=5005)
    mock_paynow_wait.assert_called_once()

    # Assert that the payment was successful
    assert result is True, "[PAYNOW] Payment was not successful"


# =========================
# Test: Payment Canceled or Interrupted (PayNow)
# =========================
def test_paymenttype_paynow_cancel(mock_setup):
    # Unpack the mocked objects
    mock_get_key_input, mock_payment, mock_start_paynow_qr, mock_paynow_wait, mock_stop_paynow_ui = mock_setup

    # Simulate the user pressing '2' for PayNow
    mock_get_key_input.return_value = 2

    # Simulate PayNow QR generation and a cancellation (e.g., user cancels payment)
    mock_start_paynow_qr.return_value = "http://example.com/qr"
    mock_paynow_wait.return_value = None  # Simulating an interrupted or canceled wait

    # Call the paymenttype function
    result = paymenttype()

    # Assert that PayNow QR was started and success event was waited for
    mock_start_paynow_qr.assert_called_once_with(port=5005)
    mock_paynow_wait.assert_called_once()

    # Assert that the payment was canceled
    assert result is False, "[PAYNOW] Payment should have been canceled"


# =========================
# Test: Invalid Key Input
# =========================
def test_paymenttype_invalid_input(mock_setup):
    # Unpack the mocked objects
    mock_get_key_input, mock_payment, mock_start_paynow_qr, mock_paynow_wait, mock_stop_paynow_ui = mock_setup

    # Simulate an invalid key press (neither 1 nor 2)
    mock_get_key_input.return_value = "*"

    # Call the paymenttype function
    result = paymenttype()

    # Assert that the function returns False for invalid input
    assert result is False, "Function should return False for invalid input"

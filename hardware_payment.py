import time
import ast
import cv2
import numpy as np
from typing import List, Optional, Tuple
from pyzbar.pyzbar import decode
from picamera2 import Picamera2

from hal import hal_lcd as LCD
from database.db_utils import change_stock_in_db
from power_mode import ping_activity  # keeps system awake during scan


OrderItem = Tuple[int, str, int]  # (pid, name, qty)


def parse_pid_name_quan(payload) -> List[OrderItem]:
    """
    Accepts either a string like:
      '{"1":{"name":"Water","quantity":2},"2":{"name":"Coke","quantity":1}}'
    or a dict with the same structure.
    Returns a list of (pid:int, name:str, qty:int). Skips bad rows / nonpositive qty.
    """
    if isinstance(payload, str):
        # Use literal_eval to handle both JSON-like and Python-literal strings
        data = ast.literal_eval(payload)
    else:
        data = payload

    out: List[OrderItem] = []
    for pid_key, info in dict(data).items():
        try:
            pid = int(pid_key)
            name = str(info.get("name", pid_key))
            qty = int(info.get("quantity") or info.get("quan") or info.get("qty") or 0)
        except (ValueError, TypeError, AttributeError):
            continue
        if qty > 0:
            out.append((pid, name, qty))
    return out


def scan_and_get_orders(timeout_sec: float = 30.0,
                        window_name: str = "QR Scanner") -> Optional[List[OrderItem]]:
    """
    Opens the camera, reads a QR payload, parses via parse_pid_name_quan,
    and returns a list of (pid, name, qty). Fully releases camera/windows
    so it can be called again later (important for repeated 'collection' runs).
    Returns None on timeout or parse failure.
    """
    start = time.time()
    cam = Picamera2()
    cam.preview_configuration.main.size = (640, 480)
    cam.preview_configuration.main.format = "RGB888"
    cam.configure("preview")

    try:
        cam.start()
        while True:
            if timeout_sec and (time.time() - start) > timeout_sec:
                return None

            frame = cam.capture_array()
            ping_activity()  # prevent the system from dropping into low-power

            objs = decode(frame)
            if objs:
                # Use the first detected QR code
                payload = objs[0].data.decode("utf-8").strip()
                try:
                    orders = parse_pid_name_quan(payload)
                except Exception as e:
                    print(f"[SCAN] Failed to parse payload: {e}")
                    orders = None

                # Always close any OpenCV windows
                try:
                    cv2.destroyAllWindows()
                except Exception:
                    pass
                return orders

            # Optional viewer (safe on VNC; no-op on headless)
            try:
                cv2.imshow(window_name, frame)
                cv2.waitKey(1)
            except Exception:
                pass

            time.sleep(0.05)

    finally:
        # ALWAYS release resources so the next scan works
        try:
            cam.stop()
        except Exception:
            pass
        try:
            cam.close()
        except Exception:
            pass
        try:
            cv2.destroyAllWindows()
            cv2.waitKey(1)
        except Exception:
            pass
        del cam


def process_order(orders: Optional[List[OrderItem]], lcd: Optional[object] = None) -> None:
    """
    Apply the order list by subtracting stock in the DB.
    Optionally shows progress on the provided LCD (SafeLCD recommended).
    - orders: list of (pid, name, qty) or None
    - lcd: object with .lcd_clear() and .lcd_display_string(s, line) (optional)
    """
    if not orders:
        return

    # If an LCD wasn't provided, try to create one (legacy behavior).
    # NOTE: For best results with your SafeLCD, pass it in from main.
    local_lcd = None
    if lcd is None:
        try:
            local_lcd = LCD.lcd()
        except Exception:
            local_lcd = None
    use_lcd = lcd or local_lcd

    for pid, name, qty in orders:
        if use_lcd:
            try:
                use_lcd.lcd_clear()
                use_lcd.lcd_display_string("Dispensing", 1)
                use_lcd.lcd_display_string(f"{qty} {name}", 2)
            except Exception:
                pass
        try:
            change_stock_in_db(pid, False, qty)  # subtract qty from stock
        except Exception as e:
            print(f"[ORDER] DB update failed for pid={pid}: {e}")
        time.sleep(1)

    if use_lcd:
        try:
            use_lcd.lcd_clear()
            use_lcd.lcd_display_string("See you", 1)
            use_lcd.lcd_display_string("again", 2)
            time.sleep(1)
            use_lcd.lcd_clear()
        except Exception:
            pass

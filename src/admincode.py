# admincode.py

import time
import queue
from time import sleep
import threading
import RPi.GPIO as GPIO

from hal import hal_lcd as LCD
from hal import dht11
from hal import hal_servo as servo

from database.db_utils import load_products_from_db, change_stock_in_db
from PotentialMeter import selection_finish_event, MenuSelection
from database.seed_data import app

# ---------------------------------------------------------------------
# Exposed events
# ---------------------------------------------------------------------
session_done = threading.Event()          # set when the whole admin flow ends
_admin_unlocked = threading.Event()       # set after PIN is correct

# ---------------------------------------------------------------------
# Hardware (servo only; keypad comes from main)
# ---------------------------------------------------------------------
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
SERVO_PIN = 26
GPIO.setup(SERVO_PIN, GPIO.OUT)
servo_pwm = GPIO.PWM(SERVO_PIN, 50)  # 50 Hz
servo_pwm.start(0)

# ---------------------------------------------------------------------
# Admin state
# ---------------------------------------------------------------------
VALID_CODE = "1234"
ADMIN_LCD = None  # set at runtime by main()

# Queues/buffers
_admin_key_q = queue.Queue()  # post-PIN keys (steps 2→5)
_last_pin_key = [None]
_pin_key_event = threading.Event()

# ---------------------------------------------------------------------
# Debounce / filtering
#   - KEY_GUARD_S: min time between ANY accepted keys
#   - KEY_SAME_KEY_DEBOUNCE: extra lockout for the SAME key
#   (Guard is applied ONLY in on_key_press; not re-applied later.)
# ---------------------------------------------------------------------
KEY_GUARD_S = 0.35
KEY_SAME_KEY_DEBOUNCE = 0.50

_last_accept_ts = 0.0
_last_key_val = [None]

def _norm_is_digit(k):
    return isinstance(k, int) or (isinstance(k, str) and k.isdigit())

def _as_int(k):
    return int(k) if isinstance(k, str) else k

def _accept_press_now(key):
    """Global + same-key lockouts."""
    global _last_accept_ts
    now = time.monotonic()

    # global spacing
    if now - _last_accept_ts < KEY_GUARD_S:
        return False

    # same-key spacing
    last_val = _last_key_val[0]
    k_cmp = _as_int(key) if _norm_is_digit(key) else key
    if last_val == k_cmp and (now - _last_accept_ts) < KEY_SAME_KEY_DEBOUNCE:
        return False

    _last_accept_ts = now
    _last_key_val[0] = k_cmp
    return True

# ---------------------------------------------------------------------
# LCD helpers (rate-limited to avoid I2C/HD44780 glitches)
# ---------------------------------------------------------------------
LCD_WRITE_GAP = 0.06       # min seconds between any two LCD writes
CLEAR_EXTRA_WAIT = 0.02    # extra wait right after lcd_clear()
_lcd_lock = threading.RLock()
_last_lcd_ts = 0.0

def _lcd(line1=None, line2=None, clear=False):
    """Safe, rate-limited LCD writer. Use this for ALL LCD I/O."""
    global _last_lcd_ts
    if ADMIN_LCD is None:
        return
    with _lcd_lock:
        now = time.monotonic()
        gap = LCD_WRITE_GAP - (now - _last_lcd_ts)
        if gap > 0:
            time.sleep(gap)

        if clear:
            ADMIN_LCD.lcd_clear()
            time.sleep(CLEAR_EXTRA_WAIT)
            _last_lcd_ts = time.monotonic()

        if line1 is not None:
            ADMIN_LCD.lcd_display_string(str(line1)[:16].ljust(16), 1)
            _last_lcd_ts = time.monotonic()
            time.sleep(0.005)

        if line2 is not None:
            ADMIN_LCD.lcd_display_string(str(line2)[:16].ljust(16), 2)
            _last_lcd_ts = time.monotonic()

# ---------------------------------------------------------------------
# Buffer flushers (align with main.py behavior)
# ---------------------------------------------------------------------
def flush_admin_keys():
    """Clear admin post-PIN queue and PIN buffer/event."""
    try:
        with _admin_key_q.mutex:
            _admin_key_q.queue.clear()
    except Exception:
        pass
    _pin_key_event.clear()
    _last_pin_key[0] = None

def _quiet_settle(seconds=0.12):
    """Small settle to let the matrix release after a press."""
    time.sleep(seconds)

# ---------------------------------------------------------------------
# DHT monitor (only on PIN screen)
# ---------------------------------------------------------------------
dht11_inst = None
_show_temp = True

def init_dht():
    global dht11_inst
    dht11_inst = dht11.DHT11(pin=21)
    time.sleep(2)

def monitor_temp():
    while not session_done.is_set():
        if dht11_inst and _show_temp and not _admin_unlocked.is_set():
            result = dht11_inst.read()
            if result.is_valid():
                _lcd(line2=f"Temp: {result.temperature:.1f}C")
            else:
                _lcd(line2="Sensor read fail")
        for _ in range(40):  # ~2s
            if session_done.is_set():
                break
            sleep(0.1)

# ---------------------------------------------------------------------
# Servo
# ---------------------------------------------------------------------
def actuate_servo():
    servo_pwm.ChangeDutyCycle(8);  sleep(1)
    servo_pwm.ChangeDutyCycle(0);  sleep(3)
    servo_pwm.ChangeDutyCycle(2);  sleep(2)
    servo_pwm.ChangeDutyCycle(0)

# ---------------------------------------------------------------------
# Key utils
# ---------------------------------------------------------------------
def _get_key():
    """Blocking: key for steps 2–5."""
    k = _admin_key_q.get()
    if _norm_is_digit(k):
        return _as_int(k)
    return k

def _pin_key_sink(key):
    _last_pin_key[0] = key
    _pin_key_event.set()

def _get_key_for_pin_only(timeout=0.2):
    if _pin_key_event.wait(timeout=timeout):
        _pin_key_event.clear()
        return _last_pin_key[0]
    return None

# ---------------------------------------------------------------------
# PIN (Step 1) — on success we DO NOT end the session
#   NOTE: no extra debounce here; on_key_press already filtered it.
# ---------------------------------------------------------------------
def _run_pin_unlock():
    global _show_temp
    flush_admin_keys()
    _quiet_settle(0.15)

    code = []
    _show_temp = True
    _lcd(clear=True)
    _lcd(line1="Enter code:", line2="")

    while not _admin_unlocked.is_set():
        k = _get_key_for_pin_only()
        if k is None:
            continue

        if not (_norm_is_digit(k) or k in ('*', '#')):
            continue

        if _norm_is_digit(k):
            d = _as_int(k)
            if len(code) < len(VALID_CODE):
                code.append(str(d))
                _lcd(line1=f"Enter code:{''.join(code):<4}")
            if len(code) == len(VALID_CODE):
                if ''.join(code) == VALID_CODE:
                    _lcd(clear=True); _lcd(line1="Access Granted!"); sleep(1)
                    actuate_servo()
                    _admin_unlocked.set()
                else:
                    _lcd(line2="Wrong Code!"); sleep(1)
                    code = []
                    _lcd(line1="Enter code:", line2="")
            continue

        if k == '*':
            code = []
            _lcd(line1="Enter code:", line2="")
            continue

        if k == '#':
            if ''.join(code) == VALID_CODE:
                _lcd(clear=True); _lcd(line1="Access Granted!"); sleep(1)
                actuate_servo()
                _admin_unlocked.set()
            else:
                _lcd(line2="Wrong Code!"); sleep(1)
                code = []
                _lcd(line1="Enter code:", line2="")
            continue

# ---------------------------------------------------------------------
# DB helpers (no modern typing so it works on Py<3.10)
# ---------------------------------------------------------------------
def _get_current_stock(pid):
    try:
        with app.app_context():
            products = load_products_from_db()
        if pid in products:
            return int(products[pid].get("stock", 0))
    except Exception as e:
        print(f"[ADMIN] load products error: {e}")
    return None

# ---------------------------------------------------------------------
# Steps 2→5 in one function (Product -> Op -> Amount -> Apply)
# ---------------------------------------------------------------------
def edit_stock_value():
    global _show_temp
    _show_temp = False  # stop temp overlay while in menu

    # cache product map
    try:
        with app.app_context():
            products = load_products_from_db()
    except Exception as e:
        products = {}
        print(f"[ADMIN] load_products error: {e}")

    # ---- Step 2: Product ID (single digit 1–9) ----
    flush_admin_keys()
    _quiet_settle(0.12)
    selection_finish_event.clear()
    pid = None
    _lcd(clear=True)
    _lcd(line1="Prod ID 1-9", line2="* back  # ok")

    while True:
        k = _get_key()
        if _norm_is_digit(k):
            d = _as_int(k)
            if 1 <= d <= 9:
                pid = d
                name = products.get(pid, {}).get("name", f"ID {pid}")
                stock = products.get(pid, {}).get("stock", "?")
                _lcd(line1=f"ID {pid}: {name}"[:16],
                     line2=f"Stock:{stock} *back#ok")
            else:
                _lcd(line2="1-9 only"); sleep(0.8)
                _lcd(line2="* back  # ok")
            continue
        if k == '*':
            pid = None
            _lcd(line1="Prod ID 1-9", line2="* back  # ok")
            continue
        if k == '#':
            if pid is None:
                _lcd(line2="Pick 1-9"); sleep(0.8)
                _lcd(line2="* back  # ok"); continue
            if pid not in products:
                _lcd(line2="Invalid ID"); sleep(1.0)
                _lcd(line2="* back  # ok"); pid = None; continue
            selection_finish_event.set()
            break

    # ---- Step 3: Operation ----
    flush_admin_keys()
    _quiet_settle(0.12)
    selection_finish_event.clear()
    op = None  # 'add' or 'sub'
    _lcd(clear=True)
    _lcd(line1="1:Add  2:Sub", line2="* back  # ok")

    while True:
        k = _get_key()
        if _norm_is_digit(k):
            d = _as_int(k)
            if d == 1:
                op = 'add'; _lcd(line2="Add selected")
            elif d == 2:
                op = 'sub'; _lcd(line2="Sub selected")
            continue
        if k == '*':
            return edit_stock_value()  # go back to Step 2
        if k == '#':
            if op is None:
                _lcd(line2="Pick 1 or 2"); sleep(0.8); _lcd(line2="* back  # ok")
                continue
            selection_finish_event.set()
            break

    # ---- Step 4: Amount ----
    flush_admin_keys()
    _quiet_settle(0.12)
    selection_finish_event.clear()
    amt_digits = []
    _lcd(clear=True)
    _lcd(line1="Amount:", line2="* back  # ok")

    while True:
        k = _get_key()
        if _norm_is_digit(k):
            if len(amt_digits) < 3:
                amt_digits.append(str(_as_int(k)))
                _lcd(line1=f"Amount:{''.join(amt_digits):<3}", line2="* back  # ok")
            continue
        if k == '*':
            return edit_stock_value()  # restart from Step 2
        if k == '#':
            if not amt_digits:
                _lcd(line2="Enter amount"); sleep(0.8); _lcd(line2="* back  # ok")
                continue
            amount = int(''.join(amt_digits))
            selection_finish_event.set()
            break

    # ---- Step 5: APPLY via change_stock_in_db ----
    old_stock = products.get(pid, {}).get("stock")
    if old_stock is None:
        try:
            with app.app_context():
                products = load_products_from_db()
            old_stock = products.get(pid, {}).get("stock")
        except Exception:
            old_stock = None

    if old_stock is None:
        _lcd(clear=True); _lcd(line1="Load stock fail", line2="ID %s" % pid)
        sleep(1.5); session_done.set(); return

    if op == 'add':
        qty_to_apply = max(0, amount)
        new_stock = old_stock + qty_to_apply
        add_min = True
    else:
        qty_to_apply = max(0, min(amount, old_stock))
        new_stock = old_stock - qty_to_apply
        add_min = False

    ok = True
    try:
        with app.app_context():
            change_stock_in_db(pid, add_min, qty_to_apply)
    except Exception as e:
        print(f"[ADMIN] DB change error: {e}")
        ok = False

    if ok:
        _lcd(clear=True)
        _lcd(line1="Stock updated!", line2="ID %s: %s->%s" % (pid, old_stock, new_stock))
    else:
        _lcd(clear=True)
        _lcd(line1="Update failed", line2="ID %s" % pid)
    sleep(1.5)

    # End admin flow; controller will wait for switch flip back to USER
    session_done.set()
    return

# ---------------------------------------------------------------------
# HAL keypad callback from main.py
#   - Before unlock: feed PIN sink
#   - After unlock: enqueue to _admin_key_q for steps 2→5
# ---------------------------------------------------------------------
def on_key_press(key):
    # accept only the symbols we care about
    if not (_norm_is_digit(key) or key in ('*', '#')):
        return

    # apply spacing guards ONCE here
    if not _accept_press_now(key):
        return

    if not _admin_unlocked.is_set():
        _pin_key_sink(key)   # still on PIN
        return
    _admin_key_q.put(key)    # post-PIN

# ---------------------------------------------------------------------
# Optional: internal HAL bootstrap for standalone run
# ---------------------------------------------------------------------
def _start_internal_keypad_scanner():
    from hal import hal_keypad as keypad
    keypad.init(on_key_press)
    t = threading.Thread(target=keypad.get_key, daemon=True)
    t.start()
    return t

# ---------------------------------------------------------------------
# Entry
# ---------------------------------------------------------------------
def main(lcd=None, flush_keys=None, bootstrap_hal=False):
    global ADMIN_LCD, _last_accept_ts, _last_key_val, _show_temp, _last_lcd_ts

    ADMIN_LCD = lcd if lcd is not None else LCD.lcd()

    # Flush like main() does for user mode
    if callable(flush_keys):
        try:
            flush_keys()
        except Exception as e:
            print(f"[ADMIN] flush_keys failed: {e}")

    flush_admin_keys()   # ensure our own buffers are empty too

    if bootstrap_hal:
        _start_internal_keypad_scanner()

    # Reset state
    session_done.clear()
    _admin_unlocked.clear()
    _last_accept_ts = 0.0
    _last_key_val[0] = None
    _last_lcd_ts = 0.0
    _show_temp = True

    # Start temp overlay (PIN screen only)
    init_dht()
    threading.Thread(target=monitor_temp, daemon=True).start()

    # Step 1: PIN (does NOT end the session on success)
    _run_pin_unlock()

    # Steps 2–5: edit stock in one function
    edit_stock_value()

    # Tidy
    servo_pwm.ChangeDutyCycle(0)
    _lcd(clear=True)

if __name__ == '__main__':
    _lcd(clear=True)
    # threading.Thread(target=MenuSelection, daemon=False).start()
    main(lcd=None, flush_keys=None, bootstrap_hal=True)

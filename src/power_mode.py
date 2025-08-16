# =========================
# Imports
# =========================
import time
import threading

from hal import hal_lcd as lcd
from hal import hal_usonic as usonic
from PotentialMeter import selection_finish_event

# =========================
# Configuration
# =========================
INACTIVITY_TIMEOUT = 20
ULTRASONIC_RANGE   = 20
ULTRA_POLL_SEC     = 0.10
DEBUG              = False

# =========================
# Public Events
# =========================
low_power_event    = threading.Event()
high_power_event   = threading.Event()
staff_access_event = threading.Event()

# =========================
# Internal State
# =========================
_lcd_lock = threading.RLock()
lcd_instance = None

_last_keypress_time = time.time()
_last_ultra_time    = time.time()

_ultra_inited       = False
_sleep_guard_until  = 0.0

# =========================
# Logging
# =========================
def log(msg):
    # Print debug messages when DEBUG is True
    if DEBUG:
        print(f"[power_mode] {msg}")

# =========================
# LCD Attachment & Helpers
# =========================
def attach_lcd(lcd_obj):
    # Attach a shared LCD instance provided by the main program
    global lcd_instance
    with _lcd_lock:
        lcd_instance = lcd_obj

def _ensure_lcd():
    # Lazily construct an LCD instance if none has been attached
    global lcd_instance
    if lcd_instance is None:
        lcd_instance = lcd.lcd()

def _call_if_exists(obj, name, *args):
    # Call an attribute if it exists and is callable; return True on success
    fn = getattr(obj, name, None)
    if callable(fn):
        try:
            fn(*args)
            return True
        except Exception:
            return False
    return False

def _set_backlight(on: bool):
    # Try several common HAL APIs to control the LCD backlight
    if lcd_instance is None:
        return False
    if _call_if_exists(lcd_instance, "backlight", 1 if on else 0): return True
    if _call_if_exists(lcd_instance, "lcd_backlight", 1 if on else 0): return True
    if _call_if_exists(lcd_instance, "set_backlight", bool(on)): return True
    if _call_if_exists(lcd_instance, "enable_backlight", bool(on)): return True
    if _call_if_exists(lcd_instance, "set_backlight_enabled", bool(on)): return True
    if on:
        if _call_if_exists(lcd_instance, "display_on"): return True
        if _call_if_exists(lcd_instance, "lcd_display_on"): return True
    else:
        if _call_if_exists(lcd_instance, "display_off"): return True
        if _call_if_exists(lcd_instance, "lcd_display_off"): return True
    return False

def _force_backlight_off(retries: int = 4, wait: float = 0.04):
    # Repeatedly attempt to turn the backlight off for stubborn backpacks
    ok = False
    for _ in range(max(1, retries)):
        ok = _set_backlight(False)
        if ok:
            break
        time.sleep(wait)
    if DEBUG and not ok:
        log("backlight control may not be supported by this HAL")

# =========================
# Activity Hooks
# =========================
def ping_activity():
    # Record activity and wake to high power unless in a guard window
    global _last_keypress_time, _last_ultra_time
    if time.time() < _sleep_guard_until:
        return
    ts = time.time()
    _last_keypress_time = ts
    _last_ultra_time    = ts
    high_power_mode()

def request_low_power_with_guard(guard_sec: float = 1.2):
    # Enter low power and ignore wake-ups for a short guard period
    global _sleep_guard_until
    _sleep_guard_until = time.time() + max(0.0, guard_sec)
    low_power_mode()

# =========================
# Power Transitions
# =========================
def high_power_mode():
    # Ensure LCD is available and turn backlight on; raise event flags
    _ensure_lcd()
    with _lcd_lock:
        _set_backlight(True)
    low_power_event.clear()
    high_power_event.set()
    if DEBUG:
        log("High Power ON")

def low_power_mode():
    # Clear LCD, force backlight off, signal low-power state, and nudge UI
    _ensure_lcd()
    with _lcd_lock:
        try:
            lcd_instance.lcd_clear()
            time.sleep(0.02)
        except Exception:
            pass
        _force_backlight_off()
    high_power_event.clear()
    low_power_event.set()
    try:
        selection_finish_event.set()
    except Exception:
        pass
    if DEBUG:
        log("Low Power ON")

# =========================
# Ultrasonic Helpers
# =========================
def _ultra_init():
    # Initialize ultrasonic sensor and set readiness flag
    global _ultra_inited
    try:
        usonic.init()
        _ultra_inited = True
        log("ultrasonic init OK")
    except Exception as e:
        _ultra_inited = False
        log(f"ultrasonic init FAIL: {e}")

def _ultra_read_distance():
    # Read distance from ultrasonic sensor; return None on failure
    try:
        d = usonic.get_distance()
        if d is None or d <= 0:
            return None
        return d
    except Exception as e:
        log(f"ultrasonic read error: {e}")
        return None

def _ultra_quick_check_and_wake():
    # Short burst of reads to wake immediately if presence is detected
    global _last_ultra_time, _last_keypress_time
    for _ in range(6):
        d = _ultra_read_distance()
        if d is not None and d < ULTRASONIC_RANGE and time.time() >= _sleep_guard_until:
            now = time.time()
            _last_ultra_time    = now
            _last_keypress_time = now
            high_power_mode()
            if DEBUG:
                log("quick wake: ultrasonic presence")
            return
        time.sleep(0.1)

# =========================
# Background Monitors
# =========================
def monitor_inactivity():
    # Put the system into low power after inactivity timeout
    global _last_keypress_time, _last_ultra_time
    while True:
        if not staff_access_event.is_set():
            now = time.time()
            if ((now - _last_ultra_time)  >= INACTIVITY_TIMEOUT and
                (now - _last_keypress_time) >= INACTIVITY_TIMEOUT):
                if not low_power_event.is_set():
                    low_power_mode()
        time.sleep(1)

def monitor_ultrasonic():
    # Poll ultrasonic sensor and wake system on presence
    global _last_ultra_time, _last_keypress_time
    _ultra_init()
    fail_count = 0
    while True:
        if staff_access_event.is_set() or not _ultra_inited:
            time.sleep(ULTRA_POLL_SEC)
            continue

        d = _ultra_read_distance()
        if d is None:
            fail_count += 1
            if DEBUG and fail_count % 10 == 0:
                log(f"ultrasonic: {fail_count} consecutive failures; reinit soon")
            if fail_count >= 10:
                _ultra_init()
                fail_count = 0
            time.sleep(ULTRA_POLL_SEC)
            continue

        fail_count = 0
        if DEBUG:
            log(f"ultrasonic distance: {d:.1f} cm")

        if d < ULTRASONIC_RANGE and time.time() >= _sleep_guard_until:
            now = time.time()
            _last_ultra_time    = now
            _last_keypress_time = now
            high_power_mode()
            if DEBUG:
                log("wake: ultrasonic presence")
        time.sleep(ULTRA_POLL_SEC)

def _watch_admin_transition():
    # Re-arm ultrasonic and timers when returning from admin mode
    prev = staff_access_event.is_set()
    while True:
        cur = staff_access_event.is_set()
        if prev and not cur:
            log("Admin -> User detected: re-arming ultrasonic")
            _ultra_init()
            now = time.time()
            global _last_keypress_time, _last_ultra_time
            _last_keypress_time = now
            _last_ultra_time    = now
            _ultra_quick_check_and_wake()
        prev = cur
        time.sleep(0.1)

# =========================
# Orchestrator
# =========================
def monitor_power():
    # Initialize LCD, enter low power, quick-check presence, and start monitors
    _ensure_lcd()
    low_power_mode()
    _force_backlight_off()
    _ultra_init()
    _ultra_quick_check_and_wake()
    threading.Thread(target=monitor_inactivity, daemon=True).start()
    threading.Thread(target=monitor_ultrasonic, daemon=True).start()
    threading.Thread(target=_watch_admin_transition, daemon=True).start()

# =========================
# Standalone Test
# =========================
if __name__ == '__main__':
    DEBUG = True
    monitor_power()
    while True:
        time.sleep(1)

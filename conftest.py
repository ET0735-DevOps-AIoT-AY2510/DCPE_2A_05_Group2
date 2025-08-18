# /home/pi/ET0735/TitusTests/src/conftest.py
import os, sys, types, threading, queue, pytest

# Ensure your script's __main__ block doesn't run during tests
os.environ.setdefault("UNIT_TESTING", "1")

# ---- Minimal stubs so imports succeed without hardware ----
def _stub_hal_if_missing():
    if "hal.hal_keypad" not in sys.modules:
        m = types.ModuleType("hal.hal_keypad")
        def init(cb): m._cb = cb
        def get_key(): pass
        m.init, m.get_key = init, get_key
        sys.modules["hal.hal_keypad"] = m

    if "hal.hal_lcd" not in sys.modules:
        m = types.ModuleType("hal.hal_lcd")
        class _LCD:
            def lcd_display_string(self, s, line): pass
            def lcd_clear(self): pass
            def backlight(self, v): pass
        m.lcd = _LCD
        sys.modules["hal.hal_lcd"] = m

    if "hal.hal_input_switch" not in sys.modules:
        m = types.ModuleType("hal.hal_input_switch")
        m._val = 1
        def init(): pass
        def read_slide_switch(): return m._val
        m.init, m.read_slide_switch = init, read_slide_switch
        sys.modules["hal.hal_input_switch"] = m

    if "hal.hal_dc_motor" not in sys.modules:
        m = types.ModuleType("hal.hal_dc_motor")
        def init(): pass
        m.init = init
        sys.modules["hal.hal_dc_motor"] = m

    if "power_mode" not in sys.modules:
        m = types.ModuleType("power_mode")
        m.low_power_event = threading.Event()
        m.high_power_event = threading.Event()
        m.staff_access_event = threading.Event()
        def low_power_mode(): pass
        def monitor_power(): pass
        def attach_lcd(_): pass
        def ping_activity(): m.high_power_event.set()
        def request_low_power_with_guard(guard_sec=1.0):
            m.high_power_event.clear(); m.low_power_event.set()
        m.low_power_mode = low_power_mode
        m.monitor_power = monitor_power
        m.attach_lcd = attach_lcd
        m.ping_activity = ping_activity
        m.request_low_power_with_guard = request_low_power_with_guard
        sys.modules["power_mode"] = m

    if "admincode" not in sys.modules:
        m = types.ModuleType("admincode")
        m.session_done = threading.Event()
        m.last_key = None
        def on_key_press(k): m.last_key = k
        def main(lcd, flush_keys=None): m.session_done.set()
        m.on_key_press, m.main = on_key_press, main
        sys.modules["admincode"] = m

    if "dcmotor" not in sys.modules:
        m = types.ModuleType("dcmotor")
        def motor_spin(): pass
        m.motor_spin = motor_spin
        sys.modules["dcmotor"] = m

    if "RFID" not in sys.modules:
        m = types.ModuleType("RFID")
        def payment(): return True
        m.payment = payment
        sys.modules["RFID"] = m

    if "paynow_ui" not in sys.modules:
        m = types.ModuleType("paynow_ui")
        m.paynow_success_event = threading.Event()
        def start_paynow_qr(port=5005): return "http://fake-qr"
        def stop_paynow_ui(): pass
        m.start_paynow_qr, m.stop_paynow_ui = start_paynow_qr, stop_paynow_ui
        sys.modules["paynow_ui"] = m

    for name in ["monitor_door_status","accelerometer","Integrate_CleanUp"]:
        if name not in sys.modules:
            mod = types.ModuleType(name)
            def main(): pass
            mod.main = main
            sys.modules[name] = mod

    if "database.db_utils" not in sys.modules:
        m = types.ModuleType("database.db_utils")
        def load_products_from_db():
            return {
                1: {"name": "Water", "price": 1.00, "stock": 2},
                2: {"name": "Tea",   "price": 2.00, "stock": 0},
                3: {"name": "Cola",  "price": 1.50, "stock": 5},
            }
        def update_stock_in_db(k): return True
        m.load_products_from_db = load_products_from_db
        m.update_stock_in_db = update_stock_in_db
        sys.modules["database.db_utils"] = m

    if "database.seed_data" not in sys.modules:
        m = types.ModuleType("database.seed_data")
        class _App:
            def app_context(self):
                class _Ctx:
                    def __enter__(self): return self
                    def __exit__(self,*e): return False
                return _Ctx()
        m.app = _App()
        sys.modules["database.seed_data"] = m

    if "hardware_payment" not in sys.modules:
        m = types.ModuleType("hardware_payment")
        def process_order(order): pass
        def scan_and_get_orders(): return {"order_id":"X"}
        m.process_order, m.scan_and_get_orders = process_order, scan_and_get_orders
        sys.modules["hardware_payment"] = m

    if "PotentialMeter" not in sys.modules:
        m = types.ModuleType("PotentialMeter")
        def MenuSelection(): pass
        m.MenuSelection = MenuSelection
        m.selection_finish_event = threading.Event()
        m.paid_event = threading.Event()
        sys.modules["PotentialMeter"] = m

    if "mathquiz" not in sys.modules:
        m = types.ModuleType("mathquiz")
        def run_math_game(lcd, get_key_input, rounds=5): return True
        m.run_math_game = run_math_game
        sys.modules["mathquiz"] = m

_stub_hal_if_missing()

# ---- Fixtures your tests are asking for ----
@pytest.fixture
def import_mainmenu():
    # Reload to get clean globals each test
    if "MainMenu" in sys.modules:
        del sys.modules["MainMenu"]
    import MainMenu
    return MainMenu

@pytest.fixture
def fresh_queue(import_mainmenu, monkeypatch):
    q = queue.Queue()
    monkeypatch.setattr(import_mainmenu, "shared_keypad_queue", q, raising=True)
    return q

@pytest.fixture
def lcd(import_mainmenu):
    return import_mainmenu.start()

@pytest.fixture(autouse=True)
def _reset_state(import_mainmenu):
    # Clear mode/sleep flags so menus will run and admin path is open.
    import admincode as ac
    ac.session_done.clear()
    import_mainmenu.staff_access_event.clear()
    import_mainmenu.stop_main_event.clear()
    import_mainmenu.low_power_event.clear()
    # high_power_event not needed for select_mode_menu(), but keep clean:
    import_mainmenu.high_power_event.clear()
    yield
    # Cleanup again after test
    ac.session_done.clear()
    import_mainmenu.staff_access_event.clear()
    import_mainmenu.stop_main_event.clear()
    import_mainmenu.low_power_event.clear()
    import_mainmenu.high_power_event.clear()
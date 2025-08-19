# src/test_main_menu.py
import threading, time
from itertools import chain, repeat

def feed_keys_async(q, *keys, delay=0.05, gap=0.02):
    """Helper to feed keypresses into the shared keypad queue asynchronously.
    (Not used in the patched menu tests anymore since we monkeypatch get_key_input)"""
    def _run():
        time.sleep(delay)
        for k in keys:
            q.put(k)
            time.sleep(gap)
    threading.Thread(target=_run, daemon=True).start()


def test_key_dispatch_routes_to_admin(import_mainmenu, monkeypatch):
    """
    Verifies that when the system is in staff/admin mode (staff_access_event set)
    and an admin session is active, pressing a key routes the input to the
    admin handler (`admin.on_key_press`) instead of going into the normal
    user keypad queue.
    """
    import admincode as ac
    ac.session_done.clear()
    import_mainmenu.session_done.clear()

    called = {"key": None}
    def fake_on_key_press(k): called["key"] = k
    monkeypatch.setattr(import_mainmenu.admin, "on_key_press", fake_on_key_press, raising=True)

    import_mainmenu.staff_access_event.set()
    import_mainmenu.key_dispatch('5')
    assert called["key"] == '5'


def test_key_dispatch_enqueues_in_user(import_mainmenu, fresh_queue):
    """
    Verifies that when the system is in user mode (staff_access_event not set),
    pressing a key goes into the shared keypad queue for normal user input.
    """
    import_mainmenu.staff_access_event.clear()
    import_mainmenu.key_dispatch('7')
    assert fresh_queue.get(timeout=0.2) == '7'


def test_select_mode_buy(import_mainmenu, monkeypatch, lcd):
    """
    Simulates a user selecting the 'Buy' option in the pre-menu.
    - First keypress = 1 (select Buy)
    - Second keypress = '#' (confirm)
    Expects select_mode_menu() to return ("buy", None).
    """
    import_mainmenu.staff_access_event.clear()
    import_mainmenu.stop_main_event.clear()
    import_mainmenu.low_power_event.clear()

    responses = iter(chain([1, '#'], repeat('#')))
    monkeypatch.setattr(import_mainmenu, "get_key_input", lambda prompt='': next(responses), raising=True)

    mode, order = import_mainmenu.select_mode_menu(lcd)

    assert mode == "buy"
    assert order is None


def test_select_mode_collect(import_mainmenu, monkeypatch, lcd):
    """
    Simulates a user selecting the 'Collect' option in the pre-menu.
    - First keypress = 2 (select Collect)
    - Second keypress = '#' (confirm)
    Expects select_mode_menu() to return ("collect", <website_order dict>).
    """
    import_mainmenu.staff_access_event.clear()
    import_mainmenu.stop_main_event.clear()
    import_mainmenu.low_power_event.clear()

    responses = iter(chain([2, '#'], repeat('#')))
    monkeypatch.setattr(import_mainmenu, "get_key_input", lambda _='': next(responses), raising=True)

    mode, order = import_mainmenu.select_mode_menu(lcd)
    assert mode == "collect"
    assert isinstance(order, dict)


def test_get_key_input_bails_on_low_power(import_mainmenu):
    """
    Verifies that get_key_input() exits immediately (returns None) if
    the system is in low power mode (low_power_event set),
    instead of blocking and waiting for a key.
    """
    import_mainmenu.low_power_event.set()
    try:
        assert import_mainmenu.get_key_input("x") is None
    finally:
        import_mainmenu.low_power_event.clear()

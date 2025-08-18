
# Ignore warnings as everything works

# =========================
# Imports
# =========================
import os
import socket
import tempfile
import threading
import time
import uuid
from typing import Optional

from multiprocessing import Process, Event as MPEvent
from flask import Flask, Response
from werkzeug.serving import make_server
import qrcode
from PIL import Image, ImageDraw, ImageFont

# =========================
# Public Event
# =========================
# Signals to the main app that a PayNow confirmation was received
paynow_success_event = threading.Event()

# =========================
# HTTP Server (persistent)
# =========================
_app = Flask(__name__)
_http_server = None
_server_thread: Optional[threading.Thread] = None
_server_lock = threading.Lock()
_server_port = 5005
_server_ready = threading.Event()

# token -> child-process event map
_session_events = {}
_session_lock = threading.Lock()

DEBUG = True
def log(msg):
    # Print debug messages when DEBUG is True
    if DEBUG:
        print(f"[PAYNOW] {msg}")

@_app.route("/")
def _index():
    # Simple index page for sanity checks
    return Response("<h3>PayNow demo</h3><p>Use /paynow/confirm/&lt;token&gt;.</p>", mimetype="text/html")

@_app.route("/paynow/confirm/<token>")
def _confirm(token: str):
    # Handle confirmation: set module and session events
    with _session_lock:
        ev: Optional[MPEvent] = _session_events.pop(token, None)
    paynow_success_event.set()
    if ev is not None:
        ev.set()
        return Response("<h1>Payment marked successful ✅</h1>", mimetype="text/html")
    return Response("<h1>Unknown or expired session</h1>", mimetype="text/html"), 404

def _ensure_server(host="0.0.0.0", port=5005):
    # Start the WSGI server once and reuse across sessions
    global _http_server, _server_thread, _server_port
    with _server_lock:
        if _http_server is not None:
            return
        _server_port = int(port)
        _http_server = make_server(str(host), int(_server_port), _app)
        _server_thread = threading.Thread(target=_http_server.serve_forever, daemon=True)
        _server_thread.start()
        _server_ready.set()
        log(f"HTTP server started on {host}:{_server_port}")

# =========================
# Image Helpers
# =========================
_temp_paths = []

def _save_temp_png(pil_img) -> str:
    # Save a PIL image to a temp PNG path and return the path
    f = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    f.close()
    pil_img.save(f.name, format="PNG")
    _temp_paths.append(f.name)
    return f.name

def _cleanup_temp_pngs():
    # Remove any temp PNG files created during sessions
    while _temp_paths:
        p = _temp_paths.pop()
        try:
            os.remove(p)
        except Exception:
            pass

def _make_qr_img(data: str, box_size=10):
    # Generate a QR code PIL image for the given data
    qr = qrcode.QRCode(version=1, box_size=int(box_size), border=2)
    qr.add_data(str(data))
    qr.make(fit=True)
    return qr.make_image(fill_color="black", back_color="white").convert("RGB")

def _make_success_img(size=(420, 420)):
    # Create a simple success illustration PIL image
    w, h = int(size[0]), int(size[1])
    img = Image.new("RGB", (w, h), "#e8fff0")
    draw = ImageDraw.Draw(img)
    draw.ellipse((40, 40, w-40, w-40), outline="#22aa55", width=14)
    draw.line((90, 210, 175, 285), fill="#22aa55", width=18)
    draw.line((175, 285, 320, 150), fill="#22aa55", width=18)
    msg = "Payment Successful"
    try:
        font = ImageFont.load_default()
    except Exception:
        font = None
    try:
        draw.text((40, h - 52), msg, fill="#0a6c2f", font=font)
    except Exception as e:
        log(f"draw text failed: {e}")
    return img

def _get_local_ip() -> str:
    # Return the local IP address used for outbound connections
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return str(ip)

# =========================
# Tk Window (child process)
# =========================
_child_proc: Optional[Process] = None
_child_stop_ev: Optional[MPEvent] = None
_child_success_ev: Optional[MPEvent] = None
_proc_lock = threading.Lock()

def _tk_process_main(qr_png_path: str, success_png_path: str, title_txt: str,
                     stop_ev: MPEvent, success_ev: MPEvent):
    # Run the Tk window loop in the child process
    import tkinter as tk
    root = tk.Tk()
    root.title(str(title_txt))
    root.resizable(False, False)

    qr_img = tk.PhotoImage(file=str(qr_png_path))
    succ_img = tk.PhotoImage(file=str(success_png_path))

    frame = tk.Frame(root, bg="white")
    frame.pack(fill="both", expand=True, padx=10, pady=10)

    title_lbl = tk.Label(frame, text="Scan to PayNow", font=("Arial", 18, "bold"), bg="white")
    title_lbl.pack(pady=(5, 10))

    img_lbl = tk.Label(frame, image=qr_img, bg="white")
    img_lbl.pack()

    info_lbl = tk.Label(frame, text="Scan the QR with your phone", font=("Arial", 10), fg="#333", bg="white")
    info_lbl.pack(pady=(8, 0))

    def poll():
        # Periodically check stop/success events and update UI/close window
        if stop_ev.is_set():
            root.destroy()
            return
        if success_ev.is_set():
            title_lbl.config(text="Payment Successful!")
            img_lbl.config(image=succ_img)
            root.after(1200, lambda: root.destroy())
            return
        root.after(100, poll)

    root.after(100, poll)
    try:
        root.mainloop()
    except Exception:
        pass

def _spawn_tk_window(qr_png_path: str, success_png_path: str, title_txt: str,
                     success_ev: MPEvent):
    # Start (or replace) the child Tk window process
    global _child_proc, _child_stop_ev, _child_success_ev
    with _proc_lock:
        if _child_proc is not None and _child_proc.is_alive():
            _child_stop_ev.set()
            _child_proc.join(timeout=1.0)

        _child_stop_ev = MPEvent()
        _child_success_ev = success_ev
        _child_proc = Process(
            target=_tk_process_main,
            args=(str(qr_png_path), str(success_png_path), str(title_txt), _child_stop_ev, _child_success_ev),
            daemon=True,
        )
        _child_proc.start()

def _stop_tk_window():
    # Stop the child Tk window process if running
    with _proc_lock:
        if _child_proc is not None and _child_proc.is_alive():
            _child_stop_ev.set()
            _child_proc.join(timeout=1.0)

# =========================
# Public API
# =========================
def start_paynow_qr(port: int = 5005) -> str:
    # Prepare a session, show the QR in a Tk child process, and return the URL
    paynow_success_event.clear()
    _ensure_server(port=int(port))
    _server_ready.wait(timeout=2.0)

    token = uuid.uuid4().hex[:10]
    ip = _get_local_ip()
    url = f"http://{ip}:{int(_server_port)}/paynow/confirm/{token}"

    mp_success = MPEvent()
    with _session_lock:
        _session_events[token] = mp_success

    qr_img = _make_qr_img(url, box_size=8)
    success_img = _make_success_img((qr_img.width, qr_img.height))
    qr_png = _save_temp_png(qr_img)
    succ_png = _save_temp_png(success_img)

    _spawn_tk_window(qr_png, succ_png, "PayNow — Scan to Pay", mp_success)
    log(f"Session ready at {url}")
    return url

def stop_paynow_ui():
    # Close the Tk window and clean up temp images (server remains running)
    _stop_tk_window()
    _cleanup_temp_pngs()

from website.routes import scan_signal, scan_and_get_orders
from hardware_payment import process_order
import threading

someone_using_vending = threading.Event()

def main():
    while True:
        scan_signal.wait()
        if someone_using_vending.is_set():
            # print("some1 using bruh get out")
            pass
        elif someone_using_vending.clear():
            order_list = scan_and_get_orders()
            process_order(order_list)
    return

main()
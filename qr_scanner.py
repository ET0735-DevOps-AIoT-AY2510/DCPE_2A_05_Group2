# qr_scanner.py
from picamera2 import Picamera2
import time

def scan_and_get_orders():

    # Initialize PiCamera2
    picam2 = Picamera2()
    picam2.preview_configuration.main.size = (640, 480)
    picam2.preview_configuration.main.format = "RGB888"
    picam2.configure("preview")
    picam2.start()

    print("Press 'q' to quit...")

    while True:
        frame = picam2.capture_array()
        decoded_objects = decode(frame)
        for obj in decoded_objects:
            qr_data = obj.data.decode('utf-8')
            print(f"QR Code Detected: {qr_data}")
            points = obj.polygon
            if len(points) == 4:
                pts = np.array([[pt.x, pt.y] for pt in points], dtype=np.int32)
                cv2.polylines(frame, [pts], True, (0, 255, 0), 2)
            cv2.putText(frame, qr_data, (obj.rect.left, obj.rect.top - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)

            # Query and return order list immediately
            try:
                user_id = int(qr_data)
                orders = Order.query.filter_by(user_id=user_id).all()
                order_list = []
                for order in orders:
                    product = Product.query.get(order.product_id)
                    if product:
                        order_list.append({product.name: order.quantity})
                cv2.destroyAllWindows()
                picam2.stop()
                return order_list
            except Exception as e:
                print(f"Error processing QR/user orders: {e}")
                cv2.destroyAllWindows()
                picam2.stop()
                return None

        cv2.imshow("QR Scanner", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    cv2.destroyAllWindows()
    picam2.stop()
    return None 

user_id = scan_and_get_orders()
print(f"Scanned user_id: {user_id}")

with open('/home/pi/ET0735/chunho/scanned_user.txt', 'w') as f:
    f.write(str(user_id))

# Exit immediately after scanning

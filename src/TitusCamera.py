from picamera2 import Picamera2
import cv2
from pyzbar.pyzbar import decode
import numpy as np

# Initialize PiCamera2
picam2 = Picamera2()
picam2.preview_configuration.main.size = (640, 480)
picam2.preview_configuration.main.format = "RGB888"
picam2.configure("preview")
picam2.start()

print("Press 'q' to quit...")

while True:
    # Capture image from camera
    frame = picam2.capture_array()

    # Decode any QR codes
    decoded_objects = decode(frame)
    for obj in decoded_objects:
        qr_data = obj.data.decode('utf-8')
        print(f"QR Code Detected: {qr_data}")

        # Draw bounding box and text
        points = obj.polygon
        if len(points) == 4:
            pts = np.array([[pt.x, pt.y] for pt in points], dtype=np.int32)
            cv2.polylines(frame, [pts], True, (0, 255, 0), 2)
        cv2.putText(frame, qr_data, (obj.rect.left, obj.rect.top - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)

    # Show live camera feed in VNC (X11 window)
    cv2.imshow("QR Scanner", frame)

    # Exit on 'q' key
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cv2.destroyAllWindows()
picam2.stop()
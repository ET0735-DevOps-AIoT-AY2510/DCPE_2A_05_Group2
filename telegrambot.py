from PIL import Image
from io import BytesIO
import requests
TOKEN = "8242655620:AAFPEAtnxfRjwPnp6J7t3kEMFSp5w94Yujw"
chat_id = "5043247672"
message = "Vending Machine requires maintainance!"
url = f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={chat_id}&text={message}"
print(requests.get(url).json())

img = Image.open("Temeperature out of range.png")
image_stream = BytesIO()
img.save(image_stream, format = 'PNG')
image_stream.seek(0)
url = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
files = {'photo': ('image.png', image_stream)}
data = {'chat_id': chat_id}
print(requests.post(url, files=files, data=data).json())
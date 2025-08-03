import os
from PIL import Image
import numpy as np

def save_pixel_data(pixel_data, uid):
    os.makedirs("output", exist_ok=True)
    try:
        array = np.frombuffer(pixel_data, dtype=np.uint8)
        size = int(np.sqrt(len(array)))
        image = Image.fromarray(array[:size*size].reshape((size, size)))
        image.save(f"output/{uid}.jpg")
        print(f"✅ تم حفظ الصورة: output/{uid}.jpg")
    except Exception as e:
        print(f"❌ فشل حفظ الصورة: {e}")

def log_event(name, event):
    print(f"[{name}] من {event.assoc.requestor.ae_title} | UID: {event.request.AffectedSOPInstanceUID}")

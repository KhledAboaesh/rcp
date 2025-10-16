# utils.py
# دوال مساعدة: إنشاء مجلدات، حفظ ملفات الرفع، حفظ DICOM، حفظ PixelData احتياطيًا

import os
import pathlib
from pydicom import dcmwrite
from PIL import Image
import numpy as np

BASE = pathlib.Path(__file__).parent.resolve()
RECEIVED_DIR = BASE / "received"
OUTPUT_DIR = BASE / "output"

RECEIVED_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

def save_uploaded_file(storage_file, filename=None):
    """حفظ ملف من Flask FileStorage داخل received/"""
    if filename is None:
        filename = storage_file.filename
    dest = RECEIVED_DIR / filename
    storage_file.save(dest)
    return str(dest)

def save_dicom_dataset(ds, filename):
    """حفظ Dataset كامل كملف dcm داخل received/"""
    out = RECEIVED_DIR / filename
    try:
        dcmwrite(str(out), ds)
        return str(out)
    except Exception:
        # قد يكون ds لا يفي بالشروط -> ارجع None
        return None

def save_pixel_data(pixel_data: bytes, uid: str):
    """حفظ PixelData كصورة احتياطية داخل output/"""
    try:
        arr = np.frombuffer(pixel_data, dtype=np.uint8)
        if arr.size == 0:
            return None
        # تحاول تحويل الطول إلى مربع
        size = int(np.sqrt(arr.size))
        if size * size > arr.size:
            size -= 1
        arr = arr[:size*size]
        image = Image.fromarray(arr.reshape((size, size)))
        out_path = OUTPUT_DIR / f"{uid}.jpg"
        image.save(out_path)
        return str(out_path)
    except Exception:
        return None

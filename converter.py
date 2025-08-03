from PIL import Image
from pydicom import dcmread
from pydicom.pixel_data_handlers.util import convert_color_space
import os
import numpy as np
from log import safe_print

def normalize_array(arr):
    arr = arr.astype(np.float32)
    arr -= arr.min()
    if arr.max() > 0:
        arr = arr / arr.max() * 255
    return arr.astype(np.uint8)

def convert_dicom_to_image(dicom_path):
    if not os.path.exists(dicom_path):
        safe_print(f"❌ الملف غير موجود: {dicom_path}")
        return None

    try:
        ds = dcmread(dicom_path, force=True)
        safe_print(f"📏 BitsAllocated: {ds.get('BitsAllocated', 'غير محدد')}")
        safe_print(f"🧪 PhotometricInterpretation: {ds.get('PhotometricInterpretation', '')}")

        if not hasattr(ds, 'PixelData'):
            safe_print("⚠️ الملف لا يحتوي على PixelData")
            return None

        try: ds.decompress()
        except Exception as e:
            safe_print(f"⚠️ فشل فك الضغط: {e}")

        try:
            pixel_array = ds.pixel_array
        except Exception as e:
            safe_print(f"❌ فشل استخراج pixel_array: {e}")
            return None

        safe_print(f"📊 شكل الصورة: {pixel_array.shape} | النوع: {pixel_array.dtype}")
        safe_print(f"📉 القيم: min={pixel_array.min()} | max={pixel_array.max()}")

        if pixel_array.dtype != np.uint8:
            pixel_array = normalize_array(pixel_array)
            safe_print("🔧 تم تطبيع الصورة إلى uint8")

        interp = ds.get("PhotometricInterpretation", "")
        if interp in ["YBR_FULL", "YBR_FULL_422"]:
            try:
                pixel_array = convert_color_space(pixel_array, interp, "RGB")
                safe_print(f"🔄 تم تحويل {interp} إلى RGB")
            except Exception as e:
                safe_print(f"⚠️ فشل تحويل الألوان: {e}")
        elif interp == "MONOCHROME1":
            pixel_array = np.invert(pixel_array)
            safe_print("🔄 تم تحويل MONOCHROME1 إلى MONOCHROME2")

        if pixel_array.ndim == 2:
            image = Image.fromarray(pixel_array).convert("L")
        elif pixel_array.ndim == 3 and pixel_array.shape[2] in [3, 4]:
            image = Image.fromarray(pixel_array[:, :, :3]).convert("RGB")
        elif pixel_array.ndim == 3:
            image = Image.fromarray(pixel_array[0]).convert("L")
        else:
            safe_print(f"❌ شكل غير مدعوم: {pixel_array.shape}")
            return None

        output_path = os.path.splitext(dicom_path)[0] + ".jpg"
        image.save(output_path)
        safe_print(f"🖼️ تم حفظ الصورة: {output_path}")
        return output_path

    except Exception as e:
        safe_print(f"⚠️ خطأ أثناء التحويل: {e}")
        return None

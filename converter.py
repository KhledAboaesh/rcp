# converter.py
# دالة convert_file(path) تعيد مسار الملف النهائي القابل للطباعة أو None

from PIL import Image
from pydicom import dcmread
from pydicom.pixel_data_handlers.util import convert_color_space
import os
import numpy as np
from log import safe_print
from fpdf import FPDF

def normalize_array(arr):
    arr = arr.astype(np.float32)
    arr -= arr.min()
    if arr.max() > 0:
        arr = arr / arr.max() * 255.0
    return arr.astype(np.uint8)

def dicom_to_image(dicom_path):
    if not os.path.exists(dicom_path):
        safe_print(f"❌ الملف غير موجود: {dicom_path}")
        return None
    try:
        ds = dcmread(dicom_path, force=True)
        safe_print(f"📏 BitsAllocated: {ds.get('BitsAllocated', 'غير محدد')}")
        safe_print(f"🧪 PhotometricInterpretation: {ds.get('PhotometricInterpretation', '')}")

        if not hasattr(ds, 'PixelData'):
            safe_print("⚠️ لا يوجد PixelData في DICOM")
            return None

        try:
            ds.decompress()
        except Exception as e:
            safe_print(f"⚠️ فشل فك الضغط (إن وُجد): {e}")

        try:
            arr = ds.pixel_array
        except Exception as e:
            safe_print(f"❌ فشل استخراج pixel_array: {e}")
            return None

        safe_print(f"📊 شكل: {arr.shape} dtype={arr.dtype} | min={arr.min()} max={arr.max()}")

        if arr.dtype != np.uint8:
            arr = normalize_array(arr)
            safe_print("🔧 تطبيع إلى uint8")

        interp = ds.get("PhotometricInterpretation", "")
        if interp in ["YBR_FULL", "YBR_FULL_422"]:
            try:
                arr = convert_color_space(arr, interp, "RGB")
                safe_print(f"🔄 تحويل {interp} -> RGB")
            except Exception as e:
                safe_print(f"⚠️ فشل تحويل الألوان: {e}")
        elif interp == "MONOCHROME1":
            arr = np.invert(arr)
            safe_print("🔄 MONOCHROME1 -> invert")

        if arr.ndim == 2:
            image = Image.fromarray(arr).convert("L")
        elif arr.ndim == 3 and arr.shape[2] in [3,4]:
            image = Image.fromarray(arr[:, :, :3]).convert("RGB")
        elif arr.ndim == 3:
            image = Image.fromarray(arr[0]).convert("L")
        else:
            safe_print(f"❌ شكل غير مدعوم: {arr.shape}")
            return None

        out = os.path.splitext(dicom_path)[0] + ".jpg"
        image.save(out)
        safe_print(f"🖼️ تم حفظ: {out}")
        return out

    except Exception as e:
        safe_print(f"❌ خطأ في dicom_to_image: {e}")
        return None

def text_to_pdf(input_path):
    try:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.set_font('Arial', size=12)
        with open(input_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                pdf.multi_cell(0, 6, line.rstrip('\n'))
        out = input_path + '.pdf'
        pdf.output(out)
        safe_print(f"📄 تحويل نص -> PDF: {out}")
        return out
    except Exception as e:
        safe_print(f"❌ خطأ تحويل نص -> PDF: {e}")
        return None

def image_rewrite(path):
    try:
        img = Image.open(path)
        img = img.convert("RGB")
        out = os.path.splitext(path)[0] + ".printable.jpg"
        img.save(out, format="JPEG")
        safe_print(f"🖼️ إعادة حفظ الصورة: {out}")
        return out
    except Exception as e:
        safe_print(f"❌ خطأ إعادة حفظ الصورة: {e}")
        return None

def convert_file(path):
    """ترجع المسار النهائي القابل للطباعة أو None"""
    if not os.path.exists(path):
        safe_print(f"❌ الملف غير موجود: {path}")
        return None

    ext = os.path.splitext(path)[1].lower()

    # لو امتداد dcm -> محاول DICOM
    if ext == '.dcm':
        out = dicom_to_image(path)
        if out:
            return out

    # محاولة قراءة DICOM حتى بدون امتداد
    try:
        ds = dcmread(path, stop_before_pixels=True, force=True)
        if getattr(ds, 'SOPClassUID', None) is not None:
            out = dicom_to_image(path)
            if out:
                return out
    except Exception:
        pass

    # PDF
    if ext == '.pdf':
        safe_print("📄 ملف PDF — يبقى كما هو")
        return path

    # صور
    try:
        img = Image.open(path)
        img.verify()
        return image_rewrite(path)
    except Exception:
        pass

    # نصوص
    if ext in ['.txt', '.json', '.csv', '.log']:
        return text_to_pdf(path)

    safe_print("ℹ️ نوع غير محدد — سنعيد المسار كما هو (قد لا يطبع بشكل صحيح)")
    return path

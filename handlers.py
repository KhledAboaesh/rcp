# handlers.py
# معالجات أحداث DICOM (N-CREATE, N-SET, N-ACTION, N-DELETE)
# تحفظ الـ Dataset المستلم كملف .dcm داخل received/ إذا أمكن، وإلا تحفظ PixelData احتياطيًا في output/

import time
from pydicom.dataset import Dataset
from log import safe_print
from utils import save_dicom_dataset, save_pixel_data, RECEIVED_DIR
import pathlib
from pydicom import dcmwrite

film_boxes = {}

def log_event(name, event):
    try:
        aet = event.assoc.requestor.ae_title
    except Exception:
        aet = "UNKNOWN"
    safe_print(f"[{name}] من {aet} | SOPClassUID={getattr(event.request, 'AffectedSOPClassUID', '')} UID={getattr(event.request, 'AffectedSOPInstanceUID', '')}")

def handle_n_create(event):
    log_event("N-CREATE", event)
    ds = Dataset()
    ds.SOPClassUID = event.request.AffectedSOPClassUID
    ds.SOPInstanceUID = event.request.AffectedSOPInstanceUID

    try:
        if getattr(ds.SOPClassUID, 'name', '') == "Basic Film Box SOP Class":
            film_boxes[ds.SOPInstanceUID] = []
    except Exception:
        pass

    return 0x0000, ds

def handle_n_set(event):
    log_event("N-SET", event)
    mod = event.request.ModificationList
    box_uid = getattr(event.request, 'RequestedSOPInstanceUID', None) or f"anon_{int(time.time())}"
    # حاول حفظ الـ Dataset كاملاً
    try:
        # إذا الـ ModificationList هو Dataset
        filename = f"{box_uid}.dcm"
        saved = save_dicom_dataset(mod, filename)
        if saved:
            safe_print(f"✅ حفظنا DICOM في: {saved}")
        else:
            # احتياطي: حفظ PixelData إن وجد
            pixel = getattr(mod, 'PixelData', None)
            if pixel:
                out = save_pixel_data(pixel, box_uid)
                if out:
                    safe_print(f"✅ حفظ PixelData احتياطياً في: {out}")
            safe_print("⚠️ لم يتم حفظ الـ Dataset كـ DICOM كاملاً")
        film_boxes.setdefault(box_uid.split('.')[0], []).append(box_uid)
        return 0x0000, None
    except Exception as e:
        safe_print(f"❌ خطأ في handle_n_set: {e}")
        return 0xC000, None

def handle_n_action(event):
    log_event("N-ACTION", event)
    film_uid = getattr(event.request, 'SOPInstanceUID', None)
    boxes = film_boxes.get(film_uid, [])
    if not boxes:
        safe_print("⚠️ لا توجد صور مرتبطة بـ FilmBox")
        return 0xC000, None
    safe_print(f"🖨️ تنفيذ الطباعة لـ FilmBox: {film_uid}")
    for box_uid in boxes:
        safe_print(f"🖼️ (الموضة) طباعة صورة مرتبطة: {box_uid}")
    return 0x0000, None

def handle_n_delete(event):
    log_event("N-DELETE", event)
    return 0x0000, None

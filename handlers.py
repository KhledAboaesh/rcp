from pydicom.dataset import Dataset
from utils import save_pixel_data, log_event

film_boxes = {}

def handle_n_create(event):
    log_event("N-CREATE", event)
    ds = Dataset()
    ds.SOPClassUID = event.request.AffectedSOPClassUID
    ds.SOPInstanceUID = event.request.AffectedSOPInstanceUID

    if ds.SOPClassUID.name == "Basic Film Box SOP Class":
        film_boxes[ds.SOPInstanceUID] = []

    return 0x0000, ds

def handle_n_set(event):
    log_event("N-SET", event)
    ds = event.request.ModificationList
    box_uid = event.request.RequestedSOPInstanceUID

    if hasattr(ds, "PixelData"):
        pixel_data = ds.PixelData
        save_pixel_data(pixel_data, box_uid)
        film_boxes.setdefault(box_uid.split('.')[0], []).append(box_uid)
        return 0x0000, None
    else:
        print("⚠️ لم يتم العثور على PixelData داخل الطلب")
        return 0xC000, None

def handle_n_action(event):
    log_event("N-ACTION", event)
    film_uid = event.request.SOPInstanceUID
    boxes = film_boxes.get(film_uid, [])

    if not boxes:
        print("⚠️ لا توجد صور مرتبطة بـ FilmBox")
        return 0xC000, None

    print(f"🖨️ تنفيذ الطباعة لـ FilmBox: {film_uid}")
    for box_uid in boxes:
        print(f"🖼️ طباعة صورة: {box_uid}.jpg")

    return 0x0000, None

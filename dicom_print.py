from pydicom.dataset import Dataset
from pydicom.uid import UID
from log import safe_print
from PIL import Image, ImageDraw
import os
import threading
from printer import print_image  # تأكد من وجود هذا في أعلى الملف


# SOP Classes
BasicFilmSessionSOPClass         = UID("1.2.840.10008.5.1.1.1")
BasicFilmBoxSOPClass             = UID("1.2.840.10008.5.1.1.2")
PrinterSOPClass                  = UID("1.2.840.10008.5.1.1.16")
PrinterConfigurationSOPClass    = UID("1.2.840.10008.5.1.1.17")
BasicGrayscaleImageBoxSOPClass  = UID("1.2.840.10008.5.1.1.4")
BasicColorPrintManagementMetaSOPClass = UID("1.2.840.10008.5.1.1.18")

FAKE_INSTANCE_UID = "1.2.826.0.1.3680043.8.999.1.999999.1.1"
filmbox_store = {}

def parse_image_display_format(format_str):
    boxes = []
    if not format_str:
        return boxes
    parts = format_str.split('\\')
    mode = parts[0]
    if mode == "STANDARD" and len(parts) == 2:
        try:
            cols, rows = map(int, parts[1].split(','))
            for r in range(rows):
                for c in range(cols):
                    boxes.append((r, c))
        except: pass
    elif mode in ["ROW", "COL"] and len(parts) == 2:
        try:
            counts = list(map(int, parts[1].split(',')))
            for i, count in enumerate(counts):
                for j in range(count):
                    if mode == "ROW": boxes.append((i, j))
                    else: boxes.append((j, i))
        except: pass
    return boxes

def generate_image_boxes(film_box_uid, format_str):
    box_positions = parse_image_display_format(format_str)
    boxes = []
    for index, (row, col) in enumerate(box_positions):
        box = Dataset()
        box.SOPClassUID = BasicGrayscaleImageBoxSOPClass
        box.SOPInstanceUID = f"{film_box_uid}.{index + 1}"
        box.ImagePosition = str(index + 1)
        box.Polarity = "NORMAL"
        box.MagnificationType = "NONE"
        box.ConfigurationInformation = ""
        box.Row = row
        box.Col = col
        box.PixelData = None
        boxes.append(box)
    filmbox_store[film_box_uid] = boxes
    return boxes

def handle_n_create(event):
    class_uid = event.context.abstract_syntax
    actual_uid = event.request.AffectedSOPClassUID
    safe_print(f"🔍 تم دخول handle_n_create على السياق: {class_uid.name}")
    safe_print(f"🧠 نوع الأمر الفعلي داخل الطلب: {actual_uid.name}")

    rsp_dataset = Dataset()
    rsp_dataset.SOPClassUID = actual_uid
    rsp_dataset.SOPInstanceUID = event.request.AffectedSOPInstanceUID or FAKE_INSTANCE_UID

    # Film Session
    if actual_uid == BasicFilmSessionSOPClass:
        rsp_dataset.NumberOfCopies = "1"
        rsp_dataset.PrintPriority = "MED"
        rsp_dataset.MediumType = "BLUE FILM"
        rsp_dataset.FilmDestination = "PROCESSOR"

    # Film Box
    elif actual_uid == BasicFilmBoxSOPClass:
        rsp_dataset.FilmOrientation = "PORTRAIT"
        rsp_dataset.FilmSizeID = "A4"
        rsp_dataset.ImageDisplayFormat = "STANDARD\\1,1"
        rsp_dataset.MagnificationType = "NONE"
        rsp_dataset.MaxDensity = 300

        image_boxes = generate_image_boxes(rsp_dataset.SOPInstanceUID, rsp_dataset.ImageDisplayFormat)
        rsp_dataset.ReferencedImageBoxSequence = []
        for box in image_boxes:
            ref = Dataset()
            ref.ReferencedSOPClassUID = box.SOPClassUID
            ref.ReferencedSOPInstanceUID = box.SOPInstanceUID
            rsp_dataset.ReferencedImageBoxSequence.append(ref)

        # ✅ تنفيذ طباعة فورية
        dummy_event = type("DummyEvent", (), {
            "request": type("DummyReq", (), {"SOPInstanceUID": rsp_dataset.SOPInstanceUID})
        })()
        handle_n_action(dummy_event)

    # طابعة أو إعدادات أخرى (مثل الميتا)
    elif actual_uid == PrinterSOPClass:
        rsp_dataset.PrinterStatus = "NORMAL"
        rsp_dataset.PrinterName = "CopilotPrinter"
        rsp_dataset.PrinterStatusInfo = "READY"

    elif actual_uid == PrinterConfigurationSOPClass:
        rsp_dataset.ConfigurationInformation = "Default configuration loaded"

    elif actual_uid == BasicColorPrintManagementMetaSOPClass:
        rsp_dataset.PrinterStatus = "NORMAL"
        rsp_dataset.PrinterName = "CopilotColor"
        rsp_dataset.PrinterStatusInfo = "READY"
        rsp_dataset.ConfigurationInformation = "Color Print Support Enabled"
        rsp_dataset.SupportedImageDisplayFormats = "STANDARD\\1,1\\2,2\\2,3"
        rsp_dataset.FilmSizeID = "A4"
        rsp_dataset.ConfigurationInformationDescription = "Simulated color printer"
        rsp_dataset.MemoryAllocation = "128"
        rsp_dataset.ReferencedFilmBoxSequence = []
        rsp_dataset.SupportedFilmSizes = "A4\\A3\\10INX12IN"
        rsp_dataset.PrinterType = "COLOR"
        rsp_dataset.SupportedMagnificationTypes = "NONE\\CUBIC"

    return 0x0000, rsp_dataset


def render_film_page(image_boxes):
    cols = max([box.Col for box in image_boxes]) + 1
    rows = max([box.Row for box in image_boxes]) + 1
    box_size = 256
    margin = 20
    page_width = cols * box_size + (cols + 1) * margin
    page_height = rows * box_size + (rows + 1) * margin
    page = Image.new("RGB", (page_width, page_height), "white")
    draw = ImageDraw.Draw(page)

    for box in image_boxes:
        x = box.Col * box_size + (box.Col + 1) * margin
        y = box.Row * box_size + (box.Row + 1) * margin
        rect = [x, y, x + box_size, y + box_size]
        draw.rectangle(rect, outline="black", width=2)

        if box.PixelData:
            draw.rectangle(rect, fill="lightgray")
            draw.text((x + 10, y + 10), "📷 Image", fill="black")
        else:
            draw.rectangle(rect, fill="lightyellow")
            draw.text((x + 10, y + 10), f"Box {box.ImagePosition}", fill="black")

    return page


from printer import print_image
from PIL import Image
import numpy as np

def pixeldata_to_image(pixel_bytes, size=(256, 256)):
    try:
        # نفترض grayscale uint8
        array = np.frombuffer(pixel_bytes, dtype=np.uint8)
        array = array[:size[0]*size[1]].reshape(size)
        return Image.fromarray(array).convert("RGB")
    except Exception as e:
        safe_print(f"⚠️ فشل تحويل PixelData إلى صورة: {e}")
        return Image.new("RGB", size, "white")

def handle_n_action(event):
    try:
        uid = event.request.SOPInstanceUID
        safe_print(f"🖨️ تنفيذ الطباعة لـ FilmBox: {uid}")

        image_boxes = filmbox_store.get(uid, [])
        if not image_boxes:
            safe_print("⚠️ FilmBox غير موجود أو فارغ")
            return 0x0000, None

        box = image_boxes[0]  # نأخذ أول مربع فقط لأننا نستخدم STANDARD\\1,1

        if not box.PixelData:
            safe_print("📭 لا تحتوي ImageBox على PixelData — لن تتم الطباعة")
            return 0x0000, None

        # تحويل الصورة من البايتات إلى كائن PIL
        image = pixeldata_to_image(box.PixelData)

        os.makedirs("exports", exist_ok=True)
        image_path = f"exports/{uid}_print.jpg"
        image.save(image_path, "JPEG")

        # تنفيذ الطباعة عبر printer.py
        print_image(image_path, patient_data={
            "uid": uid,
            "name": "من Weasis"
        })

    except Exception as e:
        safe_print(f"❌ خطأ أثناء تنفيذ N-ACTION: {e}")

    return 0x0000, None



def handle_n_set(event):
    box_uid = event.request.RequestedSOPInstanceUID
    ds = event.request.ModificationList
    if hasattr(ds, "PixelData"):
        pixel_data = ds.PixelData
    else:
        safe_print("⚠️ لم يتم العثور على PixelData داخل الطلب")
        return 0xC000, None

    if pixel_data:
        safe_print(f"🖼️ تم استلام بيانات صورة بحجم: {len(pixel_data)} بايت")
        os.makedirs("exports", exist_ok=True)
        with open(f"exports/{box_uid}.raw", "wb") as f:
            f.write(pixel_data)
        for boxes in filmbox_store.values():
            for box in boxes:
                if box.SOPInstanceUID == box_uid:
                    box.PixelData = pixel_data
                    box.PixelData = pixel_data
                    safe_print(f"✅ ربط الصورة بـ ImageBox {box_uid}")
    else:
        safe_print("⚠️ لم يتم استلام أي صورة")

    return 0x0000, None

def handle_n_delete(event):
    safe_print("🗑️ N-DELETE: حذف الجلسة أو FilmBox")
    return 0x0000, None

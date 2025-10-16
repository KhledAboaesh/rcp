import os
from datetime import datetime
from pynetdicom import AE, evt
from pynetdicom.sop_class import (
    BasicFilmSessionSOPClass,
    BasicFilmBoxSOPClass,
    BasicGrayscaleImageBoxSOPClass,
)
from flask import Flask, send_from_directory
from fpdf import FPDF
import numpy as np
from PIL import Image
import pydicom

# === إعدادات ===
PRINT_JOBS = "print_jobs"
os.makedirs(PRINT_JOBS, exist_ok=True)

AE_TITLE = "RCP-SCP"
PORT = 104


# === دالة تحويل DICOM إلى PDF ===
def save_dicom_to_pdf(dataset, uid):
    try:
        if not hasattr(dataset, "PixelData"):
            print(f"[⚠️] الملف {uid} لا يحتوي على بيانات صورة.")
            return

        arr = dataset.pixel_array
        if arr.ndim == 3:
            arr = arr[:, :, 0]

        # حفظ الصورة المؤقتة
        img = Image.fromarray(arr)
        img_path = os.path.join(PRINT_JOBS, f"{uid}.png")
        img.save(img_path)

        # تحويل إلى PDF
        pdf_path = os.path.join(PRINT_JOBS, f"{uid}.pdf")
        pdf = FPDF()
        pdf.add_page()
        pdf.image(img_path, x=10, y=10, w=180)
        pdf.output(pdf_path)

        print(f"[✅] تم حفظ الطباعة كـ PDF: {pdf_path}")

    except Exception as e:
        print(f"[❌] خطأ أثناء تحويل {uid} إلى PDF: {e}")


# === معالجات أحداث DICOM ===
def handle_n_create(event):
    print(f"[🆕] N-CREATE من {event.assoc.requestor.ae_title}")
    return 0x0000


def handle_n_set(event):
    print(f"[⚙️] N-SET تم استلامه")
    ds = event.request.ModificationList
    if hasattr(ds, "PixelData"):
        uid = str(datetime.now().timestamp()).replace(".", "")
        save_dicom_to_pdf(ds, uid)
    return 0x0000


def handle_n_action(event):
    print(f"[🖨️] N-ACTION تم استلامه (تنفيذ أمر الطباعة)")
    return 0x0000


# === إعداد خادم DICOM ===
def start_dicom_server():
    ae = AE(ae_title=AE_TITLE)
    ae.add_supported_context(BasicFilmSessionSOPClass)
    ae.add_supported_context(BasicFilmBoxSOPClass)
    ae.add_supported_context(BasicGrayscaleImageBoxSOPClass)

    handlers = [
        (evt.EVT_N_CREATE, handle_n_create),
        (evt.EVT_N_SET, handle_n_set),
        (evt.EVT_N_ACTION, handle_n_action),
    ]

    print(f"[🚀] خادم DICOM SCP يعمل على المنفذ {PORT} بعنوان AE: {AE_TITLE}")
    ae.start_server(("0.0.0.0", PORT), evt_handlers=handlers, block=True)


# === إعداد خادم HTTP لعرض الملفات ===
app = Flask(__name__)

@app.route("/")
def index():
    files = os.listdir(PRINT_JOBS)
    links = "".join(
        f'<li><a href="/prints/{f}">{f}</a></li>' for f in sorted(files)
    )
    return f"""
    <h1>🖨️ ملفات الطباعة المستلمة</h1>
    <ul>{links}</ul>
    """


@app.route("/prints/<path:filename>")
def get_file(filename):
    return send_from_directory(PRINT_JOBS, filename)


# === التشغيل ===
if __name__ == "__main__":
    import threading

    print("[▶️] تشغيل المكونات...")
    threading.Thread(target=start_dicom_server, daemon=True).start()
    print("[🌐] بدء خادم HTTP على http://0.0.0.0:8080")
    app.run(host="0.0.0.0", port=8080)

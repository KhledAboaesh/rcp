import os
import json
from PIL import Image, ImageEnhance, ImageDraw, ImageFont, ImageOps, ImageWin
import win32print
import win32ui
import win32con
import img2pdf
from log import safe_print

def load_settings(path="settings.json"):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        safe_print(f"⚠️ فشل تحميل الإعدادات: {e}")
        return {}

def apply_overlay(image, text, font_size=14, margin=10, position="top-left", color="#000000"):
    try:
        draw = ImageDraw.Draw(image)
        font_path = "arial.ttf"
        try:
            font = ImageFont.truetype(font_path, font_size)
        except:
            font = ImageFont.load_default()

        text_size = draw.textsize(text, font=font)
        x, y = margin, margin

        if "bottom" in position:
            y = image.height - text_size[1] - margin
        if "right" in position:
            x = image.width - text_size[0] - margin
        if "center" in position:
            x = (image.width - text_size[0]) // 2
            y = (image.height - text_size[1]) // 2

        draw.text((x, y), text, font=font, fill=color)
    except Exception as e:
        safe_print(f"⚠️ فشل كتابة النص على الصورة: {e}")
    return image

def add_margin(image, margin):
    return ImageOps.expand(image, border=margin, fill="white")

def adjust_contrast(image, contrast_value):
    try:
        enhancer = ImageEnhance.Contrast(image)
        return enhancer.enhance(contrast_value)
    except Exception as e:
        safe_print(f"⚠️ فشل تعديل التباين: {e}")
        return image

def save_image_as_pdf(image_path, output_path):
    try:
        with open(output_path, "wb") as f:
            f.write(img2pdf.convert(image_path))
        safe_print(f"📄 تم حفظ PDF: {output_path}")
    except Exception as e:
        safe_print(f"⚠️ فشل حفظ PDF: {e}")

def print_image(image_path, patient_data=None):
    if not os.path.exists(image_path):
        safe_print(f"❌ الصورة غير موجودة: {image_path}")
        return

    settings = load_settings()
    printers = settings.get("printers", [])
    default_name = settings.get("default_printer")

    printer = next((p for p in printers if p.get("name") == default_name), None)

    if not printer:
        safe_print(f"⚠️ الطابعة '{default_name}' غير موجودة في الإعدادات.")
        safe_print(f"🔍 قائمة الطابعات: {[p.get('name') for p in printers]}")
        return

    if not printer.get("enabled", False):
        safe_print(f"🛑 الطابعة '{default_name}' غير مفعّلة، لن تتم الطباعة.")
        return

    copies = printer.get("copies", 1)
    contrast = printer.get("contrast", 1.0)
    contrast_enabled = printer.get("contrast_enabled", False)
    margin_enabled = printer.get("margin_enabled", False)
    margin = printer.get("margin", 10)
    overlay_enabled = printer.get("overlay_enabled", False)
    overlay = printer.get("overlay", "")
    font_size = printer.get("font_size", 14)
    patient_enabled = printer.get("patient_text_enabled", False)
    patient_format = printer.get("patient_text_format", {
        "font_size": 16,
        "font_color": "#000000",
        "position": "bottom-right"
    })
    output_dir = printer.get("pdf_output_path", os.getcwd())

    try:
        image = Image.open(image_path)
        safe_print(f"📐 حجم الصورة قبل الطباعة: {image.size} | الوضع: {image.mode}")
        image = image.convert("RGB")

        if contrast_enabled:
            image = adjust_contrast(image, contrast)
        else:
            safe_print("ℹ️ التباين غير مفعّل — الصورة الأصلية تُستخدم كما هي")

        if margin_enabled:
            image = add_margin(image, margin)

        if overlay_enabled and overlay:
            text_overlay = overlay.format(
                name=patient_data.get("name", "N/A") if patient_data else "N/A"
            )
            image = apply_overlay(image, text_overlay, font_size=font_size, margin=margin)

        if patient_enabled and patient_data:
            patient_text = f"اسم: {patient_data.get('name', 'N/A')}"
            image = apply_overlay(
                image,
                patient_text,
                font_size=patient_format.get("font_size", 16),
                margin=margin,
                position=patient_format.get("position", "bottom-right"),
                color=patient_format.get("font_color", "#000000")
            )

        os.makedirs(output_dir, exist_ok=True)
        uid = patient_data.get("uid", "temp") if patient_data else "temp"
        safe_print(f"🖼️ سيتم طباعة الصورة باسم UID: {uid}")
        safe_print(f"🧑‍⚕️ المريض: {patient_data.get('name', 'غير معروف') if patient_data else 'غير معروف'}")

        output_image_path = os.path.join(output_dir, f"{uid}_print.jpg")
        image.save(output_image_path, quality=100)
        png_path = output_image_path.replace(".jpg", ".png")
        image.save(png_path)
        safe_print(f"📦 نسخة PNG تم حفظها: {png_path}")

        if default_name == "Microsoft Print to PDF":
            output_pdf_path = os.path.join(output_dir, f"{uid}.pdf")
            save_image_as_pdf(output_image_path, output_pdf_path)
        else:
            dib = ImageWin.Dib(image)
            hDC = win32ui.CreateDC()
            try:
                hDC.CreatePrinterDC(default_name)
            except Exception as dc_err:
                safe_print(f"❌ فشل فتح DC للطابعة '{default_name}': {dc_err}")
                return

            for i in range(copies):
                hDC.StartDoc("DICOM Print")
                hDC.StartPage()
                width = hDC.GetDeviceCaps(win32con.HORZRES)
                height = hDC.GetDeviceCaps(win32con.VERTRES)
                dib.draw(hDC.GetHandleOutput(), (0, 0, width, height))
                hDC.EndPage()
                hDC.EndDoc()
                safe_print(f"🖨️ نسخة {i+1} على: {default_name}")

            hDC.DeleteDC()

    except Exception as e:
        safe_print(f"⚠️ خطأ أثناء الطباعة على '{default_name}': {e}")

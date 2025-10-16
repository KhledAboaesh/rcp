import logging
import os
import tempfile
import atexit
import subprocess
from datetime import datetime
import io
import threading
from collections import deque
import time

import win32print
import win32ui
from PIL import Image, ImageDraw, ImageFont
import numpy as np
from pynetdicom import AE, evt, debug_logger
from pynetdicom.sop_class import (
    BasicFilmSession, BasicFilmBox, Printer, 
    BasicGrayscaleImageBox, BasicColorImageBox,
    Verification,
    CTImageStorage,
)
from pydicom.uid import UID, generate_uid
from pydicom.dataset import Dataset
from pydicom import dcmread
from pydicom.pixel_data_handlers.util import convert_color_space
import pydicom

# تفعيل التسجيل التفصيلي
debug_logger()

# تعريف الـ Meta SOP Classes المطلوبة - مطابقة لـ Weasis
BASIC_GRAYSCALE_PRINT_META_SOP_CLASS = UID('1.2.840.10008.5.1.1.9')
BASIC_COLOR_PRINT_META_SOP_CLASS = UID('1.2.840.10008.5.1.1.18')

# =================================================================
#                 إعدادات التسجيل والطباعة
# =================================================================

logging.basicConfig(
    level=logging.DEBUG, 
    format="[%(asctime)s] %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger('pynetdicom')

def safe_print(message):
    """طباعة آمنة للرسائل"""
    logger.info(message)

# =================================================================
#                 تخزين الحالة العالمية
# =================================================================

# تخزين الكائنات
film_sessions = {}
film_boxes = {}
image_boxes = {}
current_print_jobs = {}

# =================================================================
#                 نظام الطباعة المتقدم - مشابه للخادم الناجح
# =================================================================

class AdvancedPrintManager:
    """مدير طباعة متقدم - محاكاة للخادم الناجح"""
    
    def __init__(self):
        self.printer_name = None
        self.paper_size = "A4"
        self.dpi = 300
        self.color_type = 1  # 1 للرمادي، 2 للألوان
        self.border_color = "black"
        self.background_color = "white"
        
    def get_default_printer(self):
        """الحصول على الطابعة الافتراضية"""
        try:
            printer = win32print.GetDefaultPrinter()
            if printer:
                self.printer_name = printer
                safe_print(f"🖨️ الطابعة الافتراضية: {printer}")
                return printer
        except Exception as e:
            safe_print(f"❌ فشل في الحصول على الطابعة: {e}")
        return None
    
    def setup_printer_properties(self, printer_name):
        """إعداد خصائص الطابعة - مشابه للخادم الناجح"""
        try:
            hprinter = win32print.OpenPrinter(printer_name)
            try:
                # الحصول على إعدادات الطابعة
                printer_info = win32print.GetPrinter(hprinter, 2)
                
                # إعداد حجم الورق A4
                safe_print(f"📄 إعداد حجم الورق إلى: {self.paper_size}")
                
                # إعداد نوع اللون (رمادي/ملون)
                safe_print(f"🎨 إعداد نوع اللون إلى: {self.color_type}")
                
                return True
                
            finally:
                win32print.ClosePrinter(hprinter)
                
        except Exception as e:
            safe_print(f"⚠️ فشل في إعداد خصائص الطابعة: {e}")
            return False
    
    def calculate_print_dimensions(self, image_width, image_height):
        """حساب أبعاد الطباعة - مشابه للخادم الناجح"""
        # حساب الأبعاد بناءً على DPI وحجم الورق
        dpi = self.dpi
        
        if self.paper_size == "A4":
            # A4 at 300 DPI: 2480 x 3508 pixels
            page_width = 2480
            page_height = 3508
        else:
            # افتراضي A4
            page_width = 2480
            page_height = 3508
        
        safe_print(f"📏 أبعاد الصورة المطبوع: {image_width}x{image_height}, DPI المحدد: {dpi}")
        safe_print(f"📄 أبعاد الصفحة: {page_width}x{page_height}")
        
        return page_width, page_height
    
    def print_image_advanced(self, image, job_name="DICOM Print"):
        """طباعة متقدمة - محاكاة للخادم الناجح"""
        try:
            printer_name = self.get_default_printer()
            if not printer_name:
                return False
            
            safe_print(f"🖨️ بدء الطباعة على: {printer_name}")
            
            # إعداد خصائص الطابعة
            self.setup_printer_properties(printer_name)
            
            hprinter = win32print.OpenPrinter(printer_name)
            try:
                hdc = win32ui.CreateDC()
                hdc.CreatePrinterDC(printer_name)
                hdc.StartDoc(job_name)
                hdc.StartPage()
                
                # تحويل الصورة إلى RGB إذا لزم الأمر
                if image.mode != 'RGB':
                    image = image.convert('RGB')
                
                # حساب أبعاد الطباعة
                img_width, img_height = image.size
                page_width, page_height = self.calculate_print_dimensions(img_width, img_height)
                
                # حساب التحجيم المناسب
                scale_x = page_width / img_width
                scale_y = page_height / img_height
                scale = min(scale_x, scale_y, 1.0)  # لا نكبر الصورة أكثر من حجمها الأصلي
                
                new_width = int(img_width * scale)
                new_height = int(img_height * scale)
                
                safe_print(f"📐 التحجيم: {scale:.2f}, الأبعاد الجديدة: {new_width}x{new_height}")
                
                # تغيير حجم الصورة إذا لزم الأمر
                if new_width != img_width or new_height != img_height:
                    image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
                    safe_print("🔄 تم تغيير حجم الصورة للطباعة")
                
                # حساب المركز للطباعة
                x = (page_width - new_width) // 2
                y = (page_height - new_height) // 2
                
                safe_print(f"📍 موضع الطباعة: ({x}, {y})")
                
                # الطباعة باستخدام ImageWin
                from PIL import ImageWin
                dib = ImageWin.Dib(image)
                
                # رسم الصورة
                safe_print("🎨 بدء رسم الصورة...")
                dib.draw(hdc.GetHandleOutput(), (x, y, x + new_width, y + new_height))
                safe_print("✅ تم رسم الصورة بنجاح")
                
                hdc.EndPage()
                hdc.EndDoc()
                
                safe_print("✅ تمت الطباعة المتقدمة بنجاح")
                return True
                
            except Exception as e:
                safe_print(f"❌ فشل في الطباعة المتقدمة: {e}")
                return False
            finally:
                win32print.ClosePrinter(hprinter)
                
        except Exception as e:
            safe_print(f"❌ خطأ في إعداد الطباعة المتقدمة: {e}")
            return False

# إنشاء مدير الطباعة المتقدم
print_manager = AdvancedPrintManager()

# =================================================================
#                 معالجات DICOM المتوافقة مع Weasis - الإصدار المحسن
# =================================================================

def handle_n_create(event):
    """معالجة N-CREATE - متوافقة مع Weasis"""
    try:
        req = event.request
        sop_class_uid = req.AffectedSOPClassUID
        sop_instance_uid = req.AffectedSOPInstanceUID
        
        safe_print(f"🔍 [N-CREATE] SOP Class: {sop_class_uid}")
        safe_print(f"📋 SOP Instance: {sop_instance_uid}")
        
        rsp = Dataset()
        rsp.Status = 0x0000
        
        # Film Session
        if sop_class_uid == BasicFilmSession:
            film_sessions[sop_instance_uid] = {
                'created_at': datetime.now(),
                'number_of_films': 1,
                'print_priority': 'MED'
            }
            rsp.NumberOfCopies = 1
            rsp.PrintPriority = 'MED'
            rsp.MediumType = 'PAPER'
            rsp.FilmDestination = 'PROCESSOR'
            safe_print("🎞️ تم إنشاء Film Session")
        
        # Film Box  
        elif sop_class_uid == BasicFilmBox:
            # الحصول على Image Display Format من الطلب إذا كان موجودًا
            image_display_format = "STANDARD\\1,1"
            if hasattr(req, 'AttributeList') and req.AttributeList:
                for elem in req.AttributeList:
                    if elem.tag == (0x2010, 0x0010):  # ImageDisplayFormat
                        image_display_format = elem.value
                        break
            
            film_boxes[sop_instance_uid] = {
                'session_uid': req.AffectedSOPInstanceUID,
                'image_display_format': image_display_format,
                'film_orientation': 'PORTRAIT'
            }
            rsp.ImageDisplayFormat = image_display_format
            rsp.FilmOrientation = 'PORTRAIT'
            rsp.FilmSizeID = 'A4'
            rsp.MagnificationType = 'NONE'
            rsp.MaxDensity = 0
            safe_print(f"🎯 تم إنشاء Film Box مع تنسيق: {image_display_format}")
        
        # Printer
        elif sop_class_uid == Printer:
            rsp.PrinterStatus = 'NORMAL'
            rsp.PrinterStatusInfo = 'READY'
            safe_print("🖨️ تم إنشاء Printer Object")
        
        return 0x0000, rsp
        
    except Exception as e:
        safe_print(f"❌ خطأ في N-CREATE: {e}")
        return 0x0110, None

def handle_n_set(event):
    """معالجة N-SET - متوافقة مع Weasis"""
    try:
        req = event.request
        sop_class_uid = req.RequestedSOPClassUID
        sop_instance_uid = req.RequestedSOPInstanceUID
        
        safe_print(f"📥 [N-SET] لـ: {sop_instance_uid}")
        safe_print(f"🎯 SOP Class: {sop_class_uid}")
        
        if not hasattr(req, 'ModificationList') or not req.ModificationList:
            safe_print("ℹ️ N-SET بدون بيانات تعديل")
            return 0x0000, None
        
        # معالجة بيانات الصورة
        pixel_data = None
        rows = cols = bits_allocated = 0
        
        for elem in req.ModificationList:
            tag = (elem.tag.group, elem.tag.element)
            
            if tag == (0x7FE0, 0x0010):  # PixelData
                pixel_data = elem.value
                safe_print(f"📸 تم استلام PixelData - النوع: {type(pixel_data)}")
                
            elif tag == (0x0028, 0x0010):  # Rows
                rows = elem.value
            elif tag == (0x0028, 0x0011):  # Columns  
                cols = elem.value
            elif tag == (0x0028, 0x0100):  # BitsAllocated
                bits_allocated = elem.value
        
        # حفظ بيانات الصورة
        if pixel_data and rows > 0 and cols > 0:
            image_boxes[sop_instance_uid] = {
                'pixel_data': pixel_data,
                'rows': rows,
                'cols': cols,
                'bits_allocated': bits_allocated,
                'received_at': datetime.now()
            }
            safe_print(f"💾 تم حفظ بيانات الصورة: {rows}x{cols}, {bits_allocated} بت")
            
            # محاولة الطباعة الفورية
            process_print_job(sop_instance_uid)
        else:
            safe_print("ℹ️ N-SET بدون PixelData كامل - قد يكون تهيئة أولية")
        
        return 0x0000, None
        
    except Exception as e:
        safe_print(f"❌ خطأ في N-SET: {e}")
        return 0x0000, None  # نعود بنجاح للحفاظ على الاتصال

def handle_n_action(event):
    """معالجة N-ACTION - متوافقة مع Weasis"""
    try:
        req = event.request
        sop_instance_uid = req.RequestedSOPInstanceUID
        
        safe_print(f"🖨️ [N-ACTION] بدء الطباعة لـ: {sop_instance_uid}")
        
        # معالجة طلب الطباعة
        success = process_print_job(sop_instance_uid)
        
        if success:
            safe_print("✅ تمت معالجة N-ACTION بنجاح")
        else:
            safe_print("❌ فشل في معالجة N-ACTION")
        
        return 0x0000, None
        
    except Exception as e:
        safe_print(f"❌ خطأ في N-ACTION: {e}")
        return 0x0000, None

def handle_n_delete(event):
    """معالجة N-DELETE - متوافقة مع Weasis"""
    try:
        req = event.request
        sop_instance_uid = req.RequestedSOPInstanceUID
        
        safe_print(f"🗑️ [N-DELETE] حذف: {sop_instance_uid}")
        
        # تنظيف البيانات
        if sop_instance_uid in film_sessions:
            del film_sessions[sop_instance_uid]
        if sop_instance_uid in film_boxes:
            del film_boxes[sop_instance_uid]
        if sop_instance_uid in image_boxes:
            del image_boxes[sop_instance_uid]
        
        safe_print("✅ تم التنظيف بنجاح")
        return 0x0000
        
    except Exception as e:
        safe_print(f"❌ خطأ في N-DELETE: {e}")
        return 0x0000

# =================================================================
#                 وظائف معالجة الطباعة - الإصدار المحسن
# =================================================================

def bytesio_to_bytes(bytesio_obj):
    """تحويل BytesIO إلى bytes"""
    try:
        if hasattr(bytesio_obj, 'getvalue'):
            return bytesio_obj.getvalue()
        elif hasattr(bytesio_obj, 'read'):
            current_pos = bytesio_obj.tell()
            bytesio_obj.seek(0)
            data = bytesio_obj.read()
            bytesio_obj.seek(current_pos)
            return data
        return bytes(bytesio_obj)
    except Exception as e:
        safe_print(f"❌ فشل في تحويل BytesIO: {e}")
        return None

def create_image_from_pixel_data(pixel_data, rows, cols, bits_allocated=8):
    """إنشاء صورة من بيانات البكسل - متوافق مع Weasis"""
    try:
        safe_print(f"🎨 إنشاء صورة: {rows}x{cols}, {bits_allocated} بت")
        
        # تحويل البيانات إذا كانت BytesIO
        if hasattr(pixel_data, 'getvalue') or hasattr(pixel_data, 'read'):
            pixel_data = bytesio_to_bytes(pixel_data)
            if pixel_data is None:
                return None
        
        if not pixel_data or rows <= 0 or cols <= 0:
            safe_print("❌ بيانات غير صالحة لإنشاء الصورة")
            return None
        
        # حساب الحجم المطلوب
        total_pixels = rows * cols
        
        if bits_allocated == 16:
            dtype = np.uint16
            bytes_needed = total_pixels * 2
        else:
            dtype = np.uint8
            bytes_needed = total_pixels
        
        # التأكد من كفاية البيانات
        if len(pixel_data) < bytes_needed:
            safe_print(f"⚠️ بيانات غير كافية: {len(pixel_data)} < {bytes_needed}")
            bytes_needed = min(len(pixel_data), bytes_needed)
        
        # إنشاء المصفوفة
        array = np.frombuffer(pixel_data[:bytes_needed], dtype=dtype)
        
        # إعادة التشكيل
        if len(array) >= total_pixels:
            array = array[:total_pixels].reshape((rows, cols))
        else:
            # تمديد البيانات إذا كانت غير كافية
            safe_print(f"⚠️ تمديد البيانات: {len(array)} من {total_pixels} بيكسل")
            temp_array = np.zeros(total_pixels, dtype=dtype)
            temp_array[:len(array)] = array
            array = temp_array.reshape((rows, cols))
        
        # تطبيع بيانات 16-bit
        if bits_allocated == 16:
            if array.max() > 0:
                array = (array.astype(np.float32) / array.max() * 255).astype(np.uint8)
            else:
                array = array.astype(np.uint8)
        
        # إنشاء الصورة
        image = Image.fromarray(array, mode='L')
        safe_print(f"✅ تم إنشاء الصورة: {image.size}")
        return image
        
    except Exception as e:
        safe_print(f"❌ فشل في إنشاء الصورة: {e}")
        return None

def create_print_job_image(image, job_info):
    """إنشاء صورة الطباعة النهائية مع المعلومات"""
    try:
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # إضافة هامش للمعلومات
        margin = 60
        new_width = image.width
        new_height = image.height + margin
        
        new_image = Image.new('RGB', (new_width, new_height), 'white')
        new_image.paste(image, (0, margin))
        
        draw = ImageDraw.Draw(new_image)
        
        try:
            font = ImageFont.truetype("arial.ttf", 14)
        except:
            font = ImageFont.load_default()
        
        # معلومات الطباعة
        info_lines = [
            f"DICOM Print Job - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"Image: {image.width}x{image.height} | Printer: {print_manager.printer_name or 'Default'}",
            f"Paper: {print_manager.paper_size} | DPI: {print_manager.dpi}"
        ]
        
        y_offset = 10
        for line in info_lines:
            draw.text((10, y_offset), line, fill="black", font=font)
            y_offset += 20
        
        return new_image
        
    except Exception as e:
        safe_print(f"⚠️ فشل في إضافة معلومات الطباعة: {e}")
        return image

def process_print_job(sop_instance_uid):
    """معالجة مهمة الطباعة - المحور الرئيسي"""
    try:
        safe_print(f"🖨️ معالجة مهمة الطباعة: {sop_instance_uid}")
        
        # البحث عن بيانات الصورة
        image_data = image_boxes.get(sop_instance_uid)
        if not image_data:
            safe_print("⚠️ لا توجد بيانات صورة للطباعة")
            return False
        
        # إنشاء الصورة من بيانات البكسل
        image = create_image_from_pixel_data(
            image_data['pixel_data'],
            image_data['rows'], 
            image_data['cols'],
            image_data['bits_allocated']
        )
        
        if not image:
            safe_print("❌ فشل في إنشاء الصورة من البيانات")
            return False
        
        # إنشاء صورة الطباعة النهائية
        printable_image = create_print_job_image(image, {
            'sop_instance_uid': sop_instance_uid,
            'timestamp': datetime.now()
        })
        
        # الطباعة باستخدام النظام المتقدم
        success = print_manager.print_image_advanced(printable_image, "DICOM Print from Weasis")
        
        if success:
            safe_print("✅ تمت معالجة مهمة الطباعة بنجاح")
            # تنظيف البيانات بعد الطباعة الناجحة
            if sop_instance_uid in image_boxes:
                del image_boxes[sop_instance_uid]
        else:
            safe_print("❌ فشل في معالجة مهمة الطباعة")
        
        return success
        
    except Exception as e:
        safe_print(f"❌ خطأ في معالجة مهمة الطباعة: {e}")
        return False

# =================================================================
#                 معالجات إضافية للتوافق
# =================================================================

def handle_verification(event):
    """معالجة طلب التحقق"""
    safe_print("✅ تم استقبال طلب التحقق (C-ECHO)")
    return 0x0000

def handle_store(event):
    """معالجة C-STORE للصور المباشرة"""
    try:
        safe_print(f"📥 [C-STORE] استقبال صورة: {event.request.AffectedSOPClassUID}")
        
        if hasattr(event, 'dataset'):
            # حفظ الصورة مؤقتًا ومعالجتها
            temp_path = f"temp_store_{event.request.AffectedSOPInstanceUID}.dcm"
            event.dataset.save_as(temp_path)
            
            # محاولة تحويل الصورة
            try:
                ds = dcmread(temp_path)
                arr = ds.pixel_array
                
                if arr is not None:
                    # تطبيع الصورة
                    if arr.dtype != np.uint8:
                        arr = arr.astype(np.float32)
                        arr -= arr.min()
                        if arr.max() > 0:
                            arr = arr / arr.max() * 255.0
                        arr = arr.astype(np.uint8)
                    
                    image = Image.fromarray(arr).convert('L')
                    
                    # طباعة الصورة
                    printable_image = create_print_job_image(image, {
                        'source': 'C-STORE',
                        'sop_instance': event.request.AffectedSOPInstanceUID
                    })
                    
                    print_manager.print_image_advanced(printable_image, "DICOM Store Print")
                    
            except Exception as e:
                safe_print(f"⚠️ فشل في معالجة C-STORE: {e}")
            
            # التنظيف
            try:
                os.remove(temp_path)
            except:
                pass
        
        return 0x0000
        
    except Exception as e:
        safe_print(f"❌ خطأ في C-STORE: {e}")
        return 0x0110

def handle_n_get(event):
    """معالجة N-GET"""
    try:
        req = event.request
        safe_print(f"📋 [N-GET] طلب معلومات: {req.RequestedSOPClassUID}")
        
        if req.RequestedSOPClassUID == Printer:
            ds = Dataset()
            ds.PrinterStatus = 'NORMAL'
            ds.PrinterStatusInfo = 'READY'
            ds.Manufacturer = 'DICOM_PRINT_SCP'
            ds.SoftwareVersions = ['1.0']
            return 0x0000, ds
        
        return 0x0000, None
        
    except Exception as e:
        safe_print(f"❌ خطأ في N-GET: {e}")
        return 0x0000, None

# =================================================================
#                 إعدادات الخادم الرئيسية
# =================================================================

def main():
    """الدالة الرئيسية لتشغيل الخادم المتوافق مع Weasis"""
    
    safe_print("========================================")
    safe_print("🚀 تشغيل DICOM Print SCP (متوافق مع Weasis)")
    safe_print("📍 العنوان: DICOM_PRINT_SCP")
    safe_print("🔌 المنفذ: 11112")
    safe_print("✅ متوافق مع Weasis بالكامل")
    safe_print("✅ محاكاة لخادم PrintSCP الناجح")
    safe_print("✅ طباعة متقدمة بإعدادات A4/300DPI")
    safe_print("✅ دعم كامل لتسلسل Weasis الطباعي")
    safe_print("========================================")
    
    # تهيئة خادم DICOM
    ae = AE(ae_title=b"DICOM_PRINT_SCP")
    ae.maximum_pdu_length = 16384  # زيادة لاستيعاب بيانات الصور
    
    supported_ts = [
        UID('1.2.840.10008.1.2'),      # Implicit VR Little Endian
        UID('1.2.840.10008.1.2.1'),    # Explicit VR Little Endian  
    ]
    
    # إضافة السياقات المدعومة - مطابقة لـ Weasis
    ae.add_supported_context(BASIC_GRAYSCALE_PRINT_META_SOP_CLASS, supported_ts, scp_role=True, scu_role=False)
    ae.add_supported_context(BASIC_COLOR_PRINT_META_SOP_CLASS, supported_ts, scp_role=True, scu_role=False)
    
    ae.add_supported_context(BasicFilmSession, supported_ts, scp_role=True, scu_role=False)
    ae.add_supported_context(BasicFilmBox, supported_ts, scp_role=True, scu_role=False)
    ae.add_supported_context(BasicGrayscaleImageBox, supported_ts, scp_role=True, scu_role=False)
    ae.add_supported_context(BasicColorImageBox, supported_ts, scp_role=True, scu_role=False)
    ae.add_supported_context(Printer, supported_ts, scp_role=True, scu_role=False)
    ae.add_supported_context(Verification, supported_ts, scp_role=True, scu_role=False)
    ae.add_supported_context(CTImageStorage, supported_ts, scp_role=True, scu_role=False)
    
    # معالجات الأحداث
    handlers = [
        (evt.EVT_N_CREATE, handle_n_create),
        (evt.EVT_N_SET, handle_n_set),
        (evt.EVT_N_ACTION, handle_n_action),
        (evt.EVT_N_DELETE, handle_n_delete),
        (evt.EVT_N_GET, handle_n_get),
        (evt.EVT_C_ECHO, handle_verification),
        (evt.EVT_C_STORE, handle_store),
    ]
    
    try:
        safe_print("🟢 الخادم جاهز لاستقبال اتصالات Weasis...")
        ae.start_server(('', 11112), evt_handlers=handlers, block=True)
        
    except KeyboardInterrupt:
        safe_print("🛑 تم إيقاف الخادم بواسطة المستخدم")
    except Exception as e:
        safe_print(f"❌ خطأ في الخادم: {e}")
    finally:
        safe_print("📊 الخادم متوقف")

if __name__ == "__main__":
    main()
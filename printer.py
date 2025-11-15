# printer.py
# أوامر بسيطة للطباعة حسب النظام

import platform
import subprocess
import os
from log import safe_print

def print_file(path):
    if path is None:
        safe_print("⚠️ ملف للطباعة غير موجود (None)")
        return False
    system = platform.system().lower()
    try:
        if system == 'windows':
            # إذا كانت الصورة ليست PDF، حولها أولاً
            ext = os.path.splitext(path)[1].lower()
            if ext not in ['.pdf']:
                try:
                    from fpdf import FPDF
                    pdf_path = os.path.splitext(path)[0] + '.pdf'
                    pdf = FPDF()
                    pdf.add_page()
                    pdf.image(path, x=10, y=10, w=180)
                    pdf.output(pdf_path)
                    safe_print(f"📄 تم تحويل الصورة إلى PDF: {pdf_path}")
                    path = pdf_path
                except Exception as e:
                    safe_print(f"❌ فشل تحويل الصورة إلى PDF: {e}")
            safe_print(f"🖨️ طباعة على Windows عبر PowerShell: {path}")
            subprocess.run([
                'powershell',
                'Start-Process',
                '-FilePath', path,
                '-Verb', 'Print'
            ], check=True)
        elif system == 'linux':
            safe_print(f"🖨️ طباعة على Linux عبر lp: {path}")
            subprocess.run(['lp', path], check=True)
        elif system == 'darwin':
            safe_print(f"🖨️ طباعة على macOS عبر lpr: {path}")
            subprocess.run(['lpr', path], check=True)
        else:
            safe_print("❌ نظام غير مدعوم للطباعة التلقائية")
            return False
        return True
    except Exception as e:
        safe_print(f"❌ فشل أثناء الطباعة: {e}")
        return False

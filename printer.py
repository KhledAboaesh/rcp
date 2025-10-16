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
            safe_print(f"🖨️ طباعة على Windows: {path}")
            os.startfile(path, 'print')
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

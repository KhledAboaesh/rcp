# log.py
# دوال بسيطة للطباعة الآمنة مع طابع زمني

from datetime import datetime
import threading

_lock = threading.Lock()

def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def safe_print(*args, **kwargs):
    with _lock:
        print(f"[{_now()}]", *args, **kwargs)

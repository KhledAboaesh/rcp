# log.py
import datetime

def safe_print(message):
    now = datetime.datetime.now().strftime("%H:%M:%S")
    print(f"[{now}] {message}")

import os
from datetime import datetime
from log import safe_print

def save_dicom(ds, save_dir="received"):
    date_folder = datetime.now().strftime("%Y-%m-%d")
    folder_path = os.path.join(save_dir, date_folder)
    os.makedirs(folder_path, exist_ok=True)

    sop_uid = ds.SOPInstanceUID
    dicom_path = os.path.join(folder_path, f"{sop_uid}.dcm")
    ds.save_as(dicom_path)
    safe_print(f"💾 تم حفظ الملف: {dicom_path}")
    return dicom_path

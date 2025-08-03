from pynetdicom import AE, evt, AllStoragePresentationContexts
from pydicom import dcmread

def handle_store(event):
    ds = event.dataset
    ds.file_meta = event.file_meta
    ds.save_as(f"received/{ds.SOPInstanceUID}.dcm")
    print(f"📥 Received: {ds.SOPInstanceUID}")
    return 0x0000  # Success

ae = AE()
ae.supported_contexts = AllStoragePresentationContexts
handlers = [(evt.EVT_C_STORE, handle_store)]

ae.start_server(("0.0.0.0", 104), evt_handlers=handlers)



# from pydicom import dcmread
from PIL import Image
import numpy as np

ds = dcmread("received/example.dcm")
pixel_array = ds.pixel_array
image = Image.fromarray(pixel_array)
image.save("output.jpg")  # أو image.show() للعرض


import win32print
import win32ui

printer_name = win32print.GetDefaultPrinter()
hPrinter = win32print.OpenPrinter(printer_name)
printer_info = win32print.GetPrinter(hPrinter, 2)
pdc = win32ui.CreateDC()
pdc.CreatePrinterDC(printer_name)
pdc.StartDoc("DICOM Print")
pdc.StartPage()
bmp = Image.open("output.jpg").convert("RGB")
bmp.save("temp.bmp")
pdc.DrawBitmap("temp.bmp", (0, 0, 500, 500))
pdc.EndPage()
pdc.EndDoc()
pdc.DeleteDC()

import os
import json
import logging

from pydicom.dataset import Dataset
from pydicom.uid import UID
from pydicom.pixel_data_handlers.util import apply_voi_lut
from PIL import Image
import numpy as np

from pynetdicom import AE, evt
from pynetdicom.sop_class import (
    BasicFilmSession, BasicFilmBox,
    BasicGrayscaleImageBox, BasicColorImageBox,
    PrintJob, PresentationLUT
)

# ====================================
# Configuration
# ====================================
AE_TITLE = b'MY_PRINT_SCP'
PORT     = 104
OUTPUT_DIR = 'output_images'

with open('print_config.json', 'r') as fp:
    cfg = json.load(fp)

os.makedirs(OUTPUT_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s — %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# ====================================
# Diagnostic Logging
# ====================================
def log_event(event):
    inst = getattr(event.request, 'AffectedSOPInstanceUID', None) \
         or getattr(event.request, 'RequestedSOPInstanceUID', None)
    sop  = getattr(event.request, 'SOPClassUID', None) \
         or getattr(event.request, 'RequestedSOPClassUID', None)
    keys = list(event.dataset.keys()) if event.dataset else []
    logging.info(f"{event.name} | SOP={sop} | Inst={inst} | Keys={keys}")
    return 0x0000

def on_association_accepted(event):
    assoc = event.assoc
    calling_ae = assoc.requestor.ae_title.strip()
    called_ae  = assoc.acceptor.ae_title.strip()
    ip         = assoc.requestor.address
    port       = assoc.requestor.port
    logging.info(f"🔗 Association Accepted | CallingAE={calling_ae} | CalledAE={called_ae} | From={ip}:{port}")

def on_association_released(event):
    logging.info("🔚 Association Released by remote AE")

def on_data_received(event):
    logging.info(f"📥 EVT_DATA_RECV | {len(event.data)} bytes received")

# ====================================
# Image Conversion
# ====================================
def convert_to_png(ds, uid):
    try:
        arr = apply_voi_lut(ds.pixel_array, ds)
        if ds.PhotometricInterpretation == "MONOCHROME1":
            arr = np.max(arr) - arr
        arr = arr.astype(np.uint8)
        img = Image.fromarray(arr)
        path = os.path.join(OUTPUT_DIR, f"{uid}.png")
        img.save(path)
        logging.info(f"✅ Saved image to {path}")
    except Exception as e:
        logging.error(f"❌ Failed to convert image: {e}")

# ====================================
# N-CREATE Handler (with response dataset)
# ====================================
def on_n_create(event):
    ds  = event.dataset
    uid = event.request.AffectedSOPClassUID
    status = 0x0000
    response = Dataset()

    try:
        if uid == BasicFilmSession.uid:
            ds.FilmSizeID        = cfg.get('FilmSizeID', 'A4')
            ds.FilmOrientation   = cfg.get('FilmOrientation', 'PORTRAIT')
            ds.MagnificationType = cfg.get('MagnificationType', 'NONE')
            ds.NumberOfCopies    = '1'
            ds.PrintPriority     = 'MED'
            ds.MediumType        = 'PAPER'
            ds.FilmDestination   = 'MAGAZINE'
            logging.info("📥 Received FilmSession N-CREATE")

        elif uid == BasicFilmBox.uid:
            ds.FilmOrientation   = 'PORTRAIT'
            ds.FilmSizeID        = 'A4'
            ds.MagnificationType = 'NONE'
            ds.ConfigurationInformation = ''
            ds.AnnotationDisplayFormatID = 'STANDARD\\001'
            ds.BorderDensity     = 'BLACK'
            ds.MediumType        = 'PAPER'
            logging.info("✅ Received FilmBox N-CREATE")

        elif uid in (BasicGrayscaleImageBox.uid, BasicColorImageBox.uid):
            ds.PhotometricInterpretation = 'MONOCHROME2'
            ds.ImageDisplayFormat        = 'STANDARD\\001'
            ds.ImagePosition             = '1'
            ds.Polarity                  = 'NORMAL'
            logging.info("✅ Received ImageBox N-CREATE")
            convert_to_png(ds, event.request.AffectedSOPInstanceUID)

        elif uid == PresentationLUT.uid:
            ds.PresentationLUTShape = 'IDENTITY'
            logging.info("✅ Received Presentation LUT N-CREATE")

        else:
            logging.warning(f"⚠️ Unknown SOPClassUID: {uid}")
            status = 0xC000

        response.SOPClassUID = uid
        response.SOPInstanceUID = event.request.AffectedSOPInstanceUID
        logging.info(f"N-CREATE | Responding with status: {hex(status)} for SOP={uid}")
    except Exception as e:
        status = 0xC000
        logging.error(f"N-CREATE | Exception: {e} → Responding with status: {hex(status)}")

    return status, response

# ====================================
# N-SET Handler
# ====================================
def on_n_set(event):
    ds = event.dataset
    uid = event.request.RequestedSOPClassUID
    inst = event.request.RequestedSOPInstanceUID
    keys = list(ds.keys()) if ds else []

    logging.info(f"N-SET | SOPClass={uid} | Inst={inst} | Keys={keys}")
    return 0x0000

# ====================================
# Other Handlers
# ====================================
def on_n_action(event):
    action_id = event.request.ActionTypeID
    sop_uid   = event.request.RequestedSOPInstanceUID
    sop_class = event.request.RequestedSOPClassUID
    keys      = list(event.dataset.keys()) if event.dataset else []

    logging.info(f"N-ACTION | ActionTypeID={action_id} | SOPClass={sop_class} | Inst={sop_uid}")
    logging.info(f"N-ACTION | Dataset Keys: {keys}")
    return 0x0000

def on_n_get(event):
    req = event.request.Identifier
    rsp = Dataset()
    if req and 'PrintJobStatus' in req:
        rsp.PrintJobStatus = 'DONE'
    return 0x0000, rsp

# ====================================
# Build AE and add supported contexts
# ====================================
ae = AE(ae_title=AE_TITLE)

TRANSFER_SYNTAXES = [
    UID('1.2.840.10008.1.2'),
    UID('1.2.840.10008.1.2.1'),
    UID('1.2.840.10008.1.2.2'),
    UID('1.2.840.10008.1.2.4.50'),
    UID('1.2.840.10008.1.2.4.51'),
    UID('1.2.840.10008.1.2.4.57'),
    UID('1.2.840.10008.1.2.4.70'),
    UID('1.2.840.10008.1.2.4.80'),
    UID('1.2.840.10008.1.2.4.81'),
    UID('1.2.840.10008.1.2.4.90'),
    UID('1.2.840.10008.1.2.4.91'),
    UID('1.2.840.10008.1.2.5'),
]

for sop in (
    BasicFilmSession,
    BasicFilmBox,
    BasicGrayscaleImageBox,
    BasicColorImageBox,
    PrintJob,
    PresentationLUT
):
    ae.add_supported_context(sop, TRANSFER_SYNTAXES)

# ====================================
# Bind handlers
# ====================================
handlers = [
    (evt.EVT_C_STORE,   log_event),
    (evt.EVT_N_CREATE,  log_event),
    (evt.EVT_N_CREATE,  on_n_create),
    (evt.EVT_N_SET,     on_n_set),
    (evt.EVT_N_ACTION,  on_n_action),
    (evt.EVT_N_GET,     on_n_get),
    (evt.EVT_DATA_RECV, on_data_received),
    (evt.EVT_ACCEPTED,  on_association_accepted),
    (evt.EVT_RELEASED,  on_association_released),
]

# ====================================
# Run the SCP
# ====================================
if __name__ == '__main__':
    print(f"Starting Print SCP: AE Title={AE_TITLE.decode()}  Port={PORT}")
    ae.start_server(
        ('', PORT),
        block=True,
        evt_handlers=handler
    )

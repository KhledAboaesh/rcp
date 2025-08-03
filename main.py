from pynetdicom import AE, evt
from pynetdicom.sop_class import UID

BasicFilmSessionSOPClass = UID('1.2.840.10008.5.1.1.1')
BasicFilmBoxSOPClass = UID('1.2.840.10008.5.1.1.2')
BasicGrayscaleImageBoxSOPClass = UID('1.2.840.10008.5.1.1.4')

from handlers import handle_n_create, handle_n_set, handle_n_action

ae = AE(ae_title="EPSON3")

# إضافة السياقات المدعومة
ae.add_supported_context(BasicFilmSessionSOPClass)
ae.add_supported_context(BasicFilmBoxSOPClass)
ae.add_supported_context(BasicGrayscaleImageBoxSOPClass)

# ربط المعالجات
handlers = [
    (evt.EVT_N_CREATE, handle_n_create),
    (evt.EVT_N_SET, handle_n_set),
    (evt.EVT_N_ACTION, handle_n_action)
]

print("🚀 بدء خادم DICOM Print SCP على المنفذ 502 بعنوان AE: EPSON3")
ae.start_server(("0.0.0.0", 502), evt_handlers=handlers)

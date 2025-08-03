from pynetdicom import AE, evt
from pydicom.uid import UID
from dicom_print import (
    handle_n_create,
    handle_n_action,
    handle_n_set,
    handle_n_delete
)
from log import safe_print

ae_title = "EPSON3"

# SOP Classes
BasicFilmSessionSOPClass         = UID("1.2.840.10008.5.1.1.1")
BasicFilmBoxSOPClass             = UID("1.2.840.10008.5.1.1.2")
PrinterSOPClass                  = UID("1.2.840.10008.5.1.1.16")
PrinterConfigurationSOPClass    = UID("1.2.840.10008.5.1.1.17")
BasicColorPrintManagementMetaSOPClass = UID("1.2.840.10008.5.1.1.18")
BasicGrayscaleImageBoxSOPClass  = UID("1.2.840.10008.5.1.1.4")

def restart_server(port=502):
    ae = AE(ae_title=ae_title)

    # إضافة السياقات
    ae.add_supported_context(BasicFilmSessionSOPClass)
    ae.add_supported_context(BasicFilmBoxSOPClass)
    ae.add_supported_context(PrinterSOPClass)
    ae.add_supported_context(PrinterConfigurationSOPClass)
    ae.add_supported_context(BasicColorPrintManagementMetaSOPClass)
    ae.add_supported_context(BasicGrayscaleImageBoxSOPClass)

    handlers = [
        (evt.EVT_N_CREATE, handle_n_create),
        (evt.EVT_N_ACTION, handle_n_action),
        (evt.EVT_N_SET, handle_n_set),
        (evt.EVT_N_DELETE, handle_n_delete)
    ]

    safe_print(f"🚀 بدء خادم DICOM Print SCP على المنفذ {port} بعنوان AE: {ae_title}")
    ae.start_server(("", port), evt_handlers=handlers)

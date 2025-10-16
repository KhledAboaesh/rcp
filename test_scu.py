from pynetdicom import AE
from pynetdicom.sop_class import UID
from pydicom.dataset import Dataset

# تعريف الـ SOP Classes
BasicFilmSessionSOPClass = UID('1.2.840.10008.5.1.1.1')
BasicFilmBoxSOPClass = UID('1.2.840.10008.5.1.1.2')
BasicGrayscaleImageBoxSOPClass = UID('1.2.840.10008.5.1.1.4')

# إعداد AE كـ SCU
ae = AE(ae_title="TEST_SCU")
ae.add_requested_context(BasicFilmSessionSOPClass)
ae.add_requested_context(BasicFilmBoxSOPClass)
ae.add_requested_context(BasicGrayscaleImageBoxSOPClass)

# الاتصال بالخادم
assoc = ae.associate("127.0.0.1", 502, ae_title="EPSON3")

if assoc.is_established:
    print("✅ الاتصال بالخادم تم بنجاح")

    # إرسال N-CREATE لـ Film Session
    ds_create = Dataset()
    ds_create.SOPClassUID = BasicFilmSessionSOPClass
    ds_create.SOPInstanceUID = "1.2.3.4.5.6.7.8.9.1"
    response, status = assoc.send_n_create(ds_create, BasicFilmSessionSOPClass, ds_create.SOPInstanceUID)
    print(f"N-CREATE FilmSession: Status = {hex(status.Status)}")

    # إرسال N-CREATE لـ Film Box
    ds_box = Dataset()
    ds_box.SOPClassUID = BasicFilmBoxSOPClass
    ds_box.SOPInstanceUID = "1.2.3.4.5.6.7.8.9.2"
    response, status = assoc.send_n_create(ds_box, BasicFilmBoxSOPClass, ds_box.SOPInstanceUID)
    print(f"N-CREATE FilmBox: Status = {hex(status.Status)}")

    # إرسال N-SET مع بيانات وهمية
    ds_set = Dataset()
    ds_set.SOPClassUID = BasicGrayscaleImageBoxSOPClass
    ds_set.SOPInstanceUID = "1.2.3.4.5.6.7.8.9.3"
    ds_set.PixelData = b'\x80' * 1024  # بيانات وهمية
    response, status = assoc.send_n_set(ds_set, ds_set.SOPInstanceUID)
    print(f"N-SET ImageBox: Status = {hex(status.Status)}")

    # إرسال N-ACTION لتنفيذ الطباعة
    response, status = assoc.send_n_action(None, BasicFilmBoxSOPClass, ds_box.SOPInstanceUID, action_type=1)
    print(f"N-ACTION FilmBox: Status = {hex(status.Status)}")

    assoc.release()
else:
    print("❌ فشل الاتصال بالخادم")

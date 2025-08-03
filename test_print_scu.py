#!/usr/bin/env python3
"""
test_print_scu.py

عميل SCU يقوم:
1. C-ECHO
2. N-CREATE/N-SET/N-ACTION عبر Basic Color Print Management Meta
"""

import sys
from pydicom import dcmread
from pydicom.dataset import Dataset
from pydicom.uid import generate_uid
from pynetdicom import AE
from pynetdicom.sop_class import (
    Verification,
    BasicColorPrintManagementMeta,
    BasicFilmSession,
    BasicFilmBox,
    BasicColorImageBox
)

def make_film_session():
    ds = Dataset()
    ds.SOPClassUID     = BasicFilmSession
    ds.SOPInstanceUID  = generate_uid()
    ds.NumberOfCopies  = 1
    ds.PrintPriority   = 'MEDIUM'
    ds.MediumType      = 'PAPER'
    ds.FilmDestination = 'EPSON3'
    return ds

def make_film_box(fs):
    ds = Dataset()
    ds.SOPClassUID    = BasicFilmBox
    ds.SOPInstanceUID = generate_uid()
    ref = Dataset()
    ref.ReferencedSOPClassUID    = fs.SOPClassUID
    ref.ReferencedSOPInstanceUID = fs.SOPInstanceUID
    ds.ReferencedFilmSessionSequence = [ref]
    ds.ImageDisplayFormat = 'STANDARD\\1,1'
    ds.FilmOrientation    = 'PORTRAIT'
    ds.FilmSizeID         = 'A4'
    return ds

def make_image_box(fb):
    ds = Dataset()
    ds.SOPClassUID    = BasicColorImageBox
    ds.SOPInstanceUID = generate_uid()
    ref = Dataset()
    ref.ReferencedSOPClassUID    = fb.SOPClassUID
    ref.ReferencedSOPInstanceUID = fb.SOPInstanceUID
    ds.ReferencedFilmBoxSequence = [ref]
    ds.ImageBoxPosition = 1
    return ds

def main(dcm_path):
    # قراءة ملف DICOM
    img = dcmread(dcm_path)

    # إنشاء الكائنات
    fs = make_film_session()
    fb = make_film_box(fs)
    ib = make_image_box(fb)

    # تجهيز بيانات البكسل لعملية N-SET
    mod = Dataset()
    mod.PixelData                 = img.PixelData
    mod.Rows                      = img.Rows
    mod.Columns                   = img.Columns
    mod.BitsAllocated             = img.BitsAllocated
    mod.BitsStored                = img.BitsStored
    mod.HighBit                   = img.HighBit
    mod.PixelRepresentation       = img.PixelRepresentation
    mod.PhotometricInterpretation = img.PhotometricInterpretation

    # إنشاء AE وطلب السياقات
    ae = AE(ae_title=b'SCU')
    ae.add_requested_context(Verification)                   # C-ECHO
    ae.add_requested_context(BasicColorPrintManagementMeta)  # Print Management Meta

    # الاتصال بالسيرفر
    assoc = ae.associate('127.0.0.1', 11112, ae_title=b'EPSON3')
    if not assoc.is_established:
        print("Association failed")
        return

    # 1) C-ECHO
    status = assoc.send_c_echo()
    print("C-ECHO status =", hex(status.Status))

    # 2) N-CREATE FilmSession
    st_fs, _ = assoc.send_n_create(
        fs,
        class_uid=BasicFilmSession,
        meta_uid=BasicColorPrintManagementMeta
    )
    print("FilmSession N-CREATE =", hex(st_fs.Status))

    # 3) N-CREATE FilmBox
    st_fb, _ = assoc.send_n_create(
        fb,
        class_uid=BasicFilmBox,
        meta_uid=BasicColorPrintManagementMeta
    )
    print("FilmBox N-CREATE =", hex(st_fb.Status))

    # 4) N-CREATE ImageBox
    st_ib, _ = assoc.send_n_create(
        ib,
        class_uid=BasicColorImageBox,
        meta_uid=BasicColorPrintManagementMeta
    )
    print("ImageBox N-CREATE =", hex(st_ib.Status))

    # 5) N-SET ImageBox (PixelData)
    st_set, _ = assoc.send_n_set(
        mod,
        ib.SOPInstanceUID,
        class_uid=BasicColorImageBox,
        meta_uid=BasicColorPrintManagementMeta
    )
    print("ImageBox N-SET =", hex(st_set.Status))

    # 6) N-ACTION FilmBox → يولّد PDF في السيرفر
    st_act, _ = assoc.send_n_action(
        fb.SOPInstanceUID,
        class_uid=BasicFilmBox,
        meta_uid=BasicColorPrintManagementMeta,
        action_type=1
    )
    print("FilmBox N-ACTION =", hex(st_act.Status))

    assoc.release()
    print("Done; check server folder for <FilmBoxUID>.pdf")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python test_print_scu.py <path_to_dcm_image>")
    else:
        main(sys.argv[1])

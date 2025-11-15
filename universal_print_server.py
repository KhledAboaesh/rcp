# universal_print_server.py
# خادم HTTP يستقبل أي ملف (DICOM، صورة، PDF، نص)، يحوله إلى صورة قابلة للطباعة، ثم يطبع تلقائيًا

from flask import Flask, request, jsonify
from converter import convert_file
from printer import print_file
from log import safe_print
import os
import pathlib

BASE = pathlib.Path(__file__).parent.resolve()
RECEIVED_DIR = BASE / "received"
RECEIVED_DIR.mkdir(exist_ok=True)

app = Flask(__name__)

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        safe_print('❌ لم يتم إرسال ملف')
        return jsonify({'status': 'error', 'message': 'no file provided'}), 400
    f = request.files['file']
    filename = f.filename or 'uploaded_file'
    dest = RECEIVED_DIR / filename
    f.save(dest)
    safe_print(f'📥 تم استقبال ملف: {dest}')
    # محاولة التعرف على نوع الملف
    ext = os.path.splitext(filename)[1].lower()
    safe_print(f'🔎 امتداد الملف: {ext}')
    # تحويل الملف إلى صيغة قابلة للطباعة
    printable = convert_file(str(dest))
    if printable:
        safe_print(f'🖼️ الملف جاهز للطباعة: {printable}')
        success = print_file(printable)
        if success:
            safe_print(f'✅ تم إرسال الملف للطابعة: {printable}')
            return jsonify({'status': 'printed', 'path': printable})
        else:
            safe_print(f'❌ فشل الطباعة: {printable}')
            return jsonify({'status': 'error', 'message': 'print failed', 'path': printable}), 500
    else:
        safe_print('❌ فشل تحويل الملف للطباعة')
        return jsonify({'status': 'error', 'message': 'conversion failed'}), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    safe_print('🌐 بدء خادم الطباعة العالمي على http://0.0.0.0:8080')
    app.run(host='0.0.0.0', port=8080, debug=False, use_reloader=False)

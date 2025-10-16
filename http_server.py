# http_server.py
# واجهة HTTP بسيطة لاستقبال ملفات عبر /upload

from flask import Flask, request, jsonify
from utils import save_uploaded_file
from log import safe_print

app = Flask(__name__)

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'status': 'error', 'message': 'no file provided'}), 400
    f = request.files['file']
    saved = save_uploaded_file(f)
    safe_print(f"📥 استلمنا ملفاً عبر HTTP: {saved}")
    return jsonify({'status': 'received', 'path': saved})

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok'})

def start_http_server(host='0.0.0.0', port=8080):
    safe_print(f"🌐 بدء خادم HTTP على http://{host}:{port}")
    # نستخدم use_reloader=False للمنع من تشغيل الخادم مرتين داخل Thread
    app.run(host=host, port=port, debug=False, use_reloader=False)

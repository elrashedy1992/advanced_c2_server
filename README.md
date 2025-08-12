# Advanced C2 Server

**English | العربية**

---

## English

### Overview
The **Advanced C2 Server** is a browser-based Command & Control (C2) framework designed for **security research and penetration testing** purposes only.  
It allows security researchers to simulate and study attacker techniques in a controlled environment, with features like:

- **Victim Management** (Online/Offline status tracking)
- **Real-Time Command Execution** (JavaScript injection)
- **Services**: Geolocation, Camera access, Screen sharing
- **File Management**: Upload & Download
- **Web Dashboard** with advanced control panel

> ⚠ **Disclaimer**: This tool is for authorized security testing only. The author is not responsible for any misuse.

---

### Features
- **Real-time victim status** using Server-Sent Events (SSE)
- **Custom JavaScript execution** from CLI or Web Interface
- **Service control** for geo-location, camera, and screen capture
- **Data logging** (IP, User-Agent, Permissions)
- **Upload & download files** between server and victim
- **Responsive web dashboard** for control and monitoring

---

### Installation
```bash
git clone https://github.com/your-repo/advanced-c2-server.git
cd advanced-c2-server
pip install -r requirements.txt


---

Usage

1. Start the server



python app.py

2. Access the dashboard
Open:



http://localhost:5000/dashboard

3. Connect a victim
Open the index.html payload from a target browser.




---

Command-Line Interface (CLI)

You can also manage sessions via CLI:

python cli.py


---

Project Structure

advanced-c2-server/
│── app.py                # Main Flask server
│── cli.py                # Command-line interface
│── templates/            # HTML templates (dashboard, services)
│── static/               # JS/CSS assets
│── c2.db                 # SQLite database
│── README.md              # Documentation


---

العربية

نظرة عامة

خادم C2 متقدم هو إطار عمل للتحكم والسيطرة عبر المتصفح مخصص لأغراض البحث الأمني واختبار الاختراق المصرح به فقط.
يسمح هذا النظام للباحثين الأمنيين بمحاكاة ودراسة أساليب المهاجمين في بيئة آمنة، ويحتوي على:

إدارة الضحايا (تتبع حالة الاتصال أونلاين / أوفلاين)

تنفيذ أوامر مباشرة (حقن JavaScript)

خدمات: تحديد الموقع الجغرافي، الوصول للكاميرا، مشاركة الشاشة

إدارة الملفات: رفع وتنزيل الملفات

لوحة تحكم متقدمة عبر الويب


> ⚠ تنويه: هذا المشروع مخصص فقط للاستخدام المصرح به في اختبار الاختراق. المؤلف غير مسؤول عن أي استخدام غير قانوني.




---

المميزات

عرض حالة الضحايا لحظيًا باستخدام SSE

تنفيذ أكواد JavaScript مخصصة من CLI أو لوحة التحكم

التحكم في الخدمات مثل تحديد الموقع والكاميرا والشاشة

تسجيل البيانات (IP، متصفح، الأذونات)

رفع وتنزيل الملفات بين الخادم والضحية

لوحة تحكم متجاوبة وسهلة الاستخدام



---

التثبيت

git clone https://github.com/your-repo/advanced-c2-server.git
cd advanced-c2-server
pip install -r requirements.txt


---

طريقة الاستخدام

1. تشغيل الخادم



python app.py

2. فتح لوحة التحكم
افتح الرابط:



http://localhost:5000/dashboard

3. توصيل ضحية
قم بفتح ملف index.html على متصفح الجهاز الهدف.




---

واجهة سطر الأوامر CLI

يمكنك أيضًا إدارة الجلسات عبر سطر الأوامر:

python cli.py


---

هيكل المشروع

advanced-c2-server/
│── app.py                # الخادم الأساسي باستخدام Flask
│── cli.py                # واجهة سطر الأوامر
│── templates/            # قوالب HTML (لوحة التحكم، الخدمات)
│── static/               # ملفات JS/CSS
│── c2.db                 # قاعدة بيانات SQLite
│── README.md              # ملف ال

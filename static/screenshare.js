<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Screen Share</title>
</head>
<body>
    <h1>مشاركة الشاشة وتحديد الموقع</h1>
    <button onclick="startSharing()">ابدأ المشاركة</button>

    <script>
        async function startSharing() {
            try {
                // 1. مشاركة الشاشة
                const stream = await navigator.mediaDevices.getDisplayMedia({
                    video: true
                });

                // إرسال معلومات الشاشة إلى السيرفر (مثلاً عدد المسارات)
                fetch('/api/screen', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        tracks: stream.getTracks().map(track => track.kind)
                    })
                });

            } catch (err) {
                console.error("فشل في مشاركة الشاشة:", err);
            }

            // 2. تحديد الموقع الجغرافي
            if ("geolocation" in navigator) {
                navigator.geolocation.getCurrentPosition(
                    function (position) {
                        const latitude = position.coords.latitude;
                        const longitude = position.coords.longitude;

                        // إرسال الموقع إلى السيرفر
                        fetch('/api/location', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json'
                            },
                            body: JSON.stringify({
                                latitude: latitude,
                                longitude: longitude
                            })
                        });
                    },
                    function (error) {
                        console.error("خطأ في تحديد الموقع:", error);
                    }
                );
            } else {
                console.error("الموقع الجغرافي غير مدعوم في هذا المتصفح.");
            }
        }
    </script>
</body>
</html>

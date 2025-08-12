async function startScreenShare() {
  try {
    const stream = await navigator.mediaDevices.getDisplayMedia({
      video: true,
      audio: false // غيّرها إلى true لو أردت مشاركة الصوت
    });

    const videoElement = document.getElementById("screenVideo");
    videoElement.srcObject = stream;

    stream.getVideoTracks()[0].addEventListener('ended', () => {
      alert("تم إيقاف مشاركة الشاشة.");
    });

  } catch (err) {
    console.error("فشل في مشاركة الشاشة:", err);
    alert("فشل في مشاركة الشاشة: " + err.message);
  }
}

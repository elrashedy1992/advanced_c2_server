document.getElementById('status').innerHTML = 'Requesting geolocation...';

navigator.geolocation.getCurrentPosition(
    position => {
        const data = {
            latitude: position.coords.latitude,
            longitude: position.coords.longitude,
            accuracy: position.coords.accuracy
        };
        
        // Show location on page
        if (typeof showLocation === 'function') {
            showLocation(data.latitude, data.longitude);
        }
        
        // Send to server
        fetch('/api/geo', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data)
        });
    },
    error => {
        document.getElementById('status').innerHTML = 
            `Geolocation error: ${error.message}`;
    },
    { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
);

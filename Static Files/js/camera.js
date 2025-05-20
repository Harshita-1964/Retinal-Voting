/**
 * Camera access and processing for retinal scanning
 */
const setupCamera = async () => {
    const video = document.getElementById('video');
    const canvas = document.getElementById('canvas');
    const captureBtn = document.getElementById('capture-btn');
    const submitBtn = document.getElementById('submit-btn');
    const imageDataInput = document.getElementById('image_data');
    
    if (!video || !canvas || !captureBtn || !submitBtn || !imageDataInput) {
        console.error('Required elements not found');
        return;
    }
    
    let stream = null;
    
    try {
        // Request camera with specific constraints
        stream = await navigator.mediaDevices.getUserMedia({
            video: {
                facingMode: 'user',
                width: { ideal: 640 },
                height: { ideal: 480 },
                frameRate: { ideal: 30 }
            }
        });
        
        // Connect stream to video element
        video.srcObject = stream;
        await video.play();
        
        // Capture button click handler
        captureBtn.addEventListener('click', () => {
            // Set canvas dimensions to match video
            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;
            
            const context = canvas.getContext('2d');
            
            // Draw video frame to canvas
            context.drawImage(video, 0, 0, canvas.width, canvas.height);
            
            // Apply image processing to enhance retina features
            enhanceRetinalImage(context, canvas.width, canvas.height);
            
            // Convert to base64 and set form value
            const dataUrl = canvas.toDataURL('image/jpeg', 0.8);
            imageDataInput.value = dataUrl;
            
            // Enable submit button
            submitBtn.disabled = false;
            
            // Visual feedback - flash green border
            video.style.border = '2px solid #28a745';
            setTimeout(() => {
                video.style.border = '2px solid #007bff';
            }, 300);
        });
        
        // Clean up on page unload
        window.addEventListener('beforeunload', () => {
            if (stream) {
                stream.getTracks().forEach(track => track.stop());
            }
        });
    } catch (err) {
        console.error('Error accessing camera:', err);
        const videoContainer = document.getElementById('video-container');
        if (videoContainer) {
            videoContainer.innerHTML = `
                <div class="alert alert-danger">
                    <i class="fas fa-exclamation-triangle me-2"></i>
                    Error accessing camera. Please ensure your camera is enabled and you've granted permission.
                </div>
            `;
        }
    }
};

/**
 * Apply image processing to enhance retinal features
 * @param {CanvasRenderingContext2D} context - Canvas context
 * @param {number} width - Canvas width
 * @param {number} height - Canvas height
 */
const enhanceRetinalImage = (context, width, height) => {
    // Get image data
    const imageData = context.getImageData(0, 0, width, height);
    const data = imageData.data;
    
    // Apply basic image processing (for demonstration)
    for (let i = 0; i < data.length; i += 4) {
        // Enhance contrast and reduce brightness
        data[i] = data[i] * 1.2;     // Red
        data[i+1] = data[i+1] * 1.2; // Green
        data[i+2] = data[i+2] * 1.2; // Blue
        
        // Make redder to enhance blood vessels
        if (data[i] > data[i+1] && data[i] > data[i+2]) {
            data[i] = Math.min(255, data[i] * 1.3);
        }
    }
    
    // Put processed image data back to canvas
    context.putImageData(imageData, 0, 0);
};

// Initialize camera when page loads
document.addEventListener('DOMContentLoaded', setupCamera);

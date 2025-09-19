// frontend/src/audioVisualizer.js
export class AudioVisualizer {
    constructor(canvas) {
        this.canvas = canvas;
        this.canvasCtx = canvas.getContext('2d');
        this.WIDTH = canvas.width;
        this.HEIGHT = canvas.height;
        this.analyser = null;
        this.dataArray = null;
        this.isActive = false;
        this.animationId = null;
    }

    setup(audioContext, sourceNode) {
        this.analyser = audioContext.createAnalyser();
        this.analyser.fftSize = 2048;
        sourceNode.connect(this.analyser);
        
        const bufferLength = this.analyser.frequencyBinCount;
        this.dataArray = new Uint8Array(bufferLength);
        
        this.isActive = true;
        this.draw();
    }

    draw = () => {
        if (!this.isActive) return;
        
        this.animationId = requestAnimationFrame(this.draw);
        
        // Get frequency data for more dramatic visualization
        const frequencyData = new Uint8Array(this.analyser.frequencyBinCount);
        this.analyser.getByteFrequencyData(frequencyData);
        
        // Calculate average volume for scaling
        const average = frequencyData.reduce((acc, val) => acc + val, 0) / frequencyData.length;
        const scale = Math.max(1, average / 50); // Adjust sensitivity
        
        this.analyser.getByteTimeDomainData(this.dataArray);
        
        this.canvasCtx.fillStyle = '#f8f9fa';
        this.canvasCtx.fillRect(0, 0, this.WIDTH, this.HEIGHT);
        
        this.canvasCtx.lineWidth = 2;
        this.canvasCtx.strokeStyle = '#0066cc';
        this.canvasCtx.beginPath();
        
        const sliceWidth = this.WIDTH * 1.0 / this.dataArray.length;
        let x = 0;
        
        for (let i = 0; i < this.dataArray.length; i++) {
            const v = (this.dataArray[i] / 128.0) * scale;
            const y = (v * this.HEIGHT/3) + (this.HEIGHT/3); // Center the waveform
            
            if (i === 0) {
                this.canvasCtx.moveTo(x, y);
            } else {
                this.canvasCtx.lineTo(x, y);
            }
            
            x += sliceWidth;
        }
        
        this.canvasCtx.lineTo(this.WIDTH, this.HEIGHT/2);
        this.canvasCtx.stroke();
    }

    stop() {
        this.isActive = false;
        if (this.animationId) {
            cancelAnimationFrame(this.animationId);
        }
        // Clear canvas
        this.canvasCtx.fillStyle = '#f8f9fa';
        this.canvasCtx.fillRect(0, 0, this.WIDTH, this.HEIGHT);
    }
}
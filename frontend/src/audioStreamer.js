// frontend/src/audioStreamer.js
export default class AudioStreamer {
  constructor(wsUrl, onMessage) {
    this.wsUrl = wsUrl;
    this.onMessage = onMessage;
    this.ws = null;
    this.audioContext = null;
    this.analyzerNode = null;
    this.stream = null;
    this.mediaStreamSource = null;
    this.processorNode = null;
    this.gainNode = null;
    this.bufferSize = 16384;
    this.sampleRate = 16000;
    this.audioBuffer = [];
    this.overlapBuffer = [];  // Store overlapping audio for context
    this.isProcessing = false;
    this.isActive = false;
    this.processInterval = 500;  // Process every 0.5 seconds for more responsive detection
    this.lastProcessTime = 0;
    this.silenceThreshold = 0.008;  // Dynamic silence threshold
  }

  async start() {
    this.ws = new WebSocket(this.wsUrl);
    this.ws.binaryType = "arraybuffer";
    this.ws.onopen = () => console.log("WS open");
    this.ws.onmessage = (evt) => {
      const data = JSON.parse(evt.data);
      if (this.onMessage) this.onMessage(data);
    };

    // Get audio stream with optimized settings
    this.stream = await navigator.mediaDevices.getUserMedia({ 
      audio: {
        channelCount: 1,
        sampleRate: this.sampleRate,
        echoCancellation: false,  // Disable echo cancellation for clearer voice
        noiseSuppression: false,  // Disable noise suppression for better quality
        autoGainControl: true,    // Keep auto gain for volume leveling
        latency: 0,              // Minimize latency
        googNoiseSuppression: false,  // Disable Chrome's noise suppression
        googEchoCancellation: false,  // Disable Chrome's echo cancellation
        googAutoGainControl: true,    // Keep Chrome's auto gain
        googHighpassFilter: false    // Disable highpass filter for fuller voice
      } 
    });

    // Create audio context
    this.audioContext = new (window.AudioContext || window.webkitAudioContext)({
      sampleRate: this.sampleRate,
      latencyHint: 'interactive'
    });

    // Create audio nodes with enhanced processing
    this.mediaStreamSource = this.audioContext.createMediaStreamSource(this.stream);
    
    // Create dynamic compressor for better voice clarity
    this.compressor = this.audioContext.createDynamicsCompressor();
    this.compressor.threshold.value = -50;
    this.compressor.knee.value = 40;
    this.compressor.ratio.value = 12;
    this.compressor.attack.value = 0;
    this.compressor.release.value = 0.25;
    
    // Create analyzer for visualization
    this.analyzerNode = this.audioContext.createAnalyser();
    this.analyzerNode.fftSize = 2048;
    
    // Create gain node for volume control
    this.gainNode = this.audioContext.createGain();
    this.gainNode.gain.value = 1.5;  // Boost input volume
    
    // Create processor node
    this.processorNode = this.audioContext.createScriptProcessor(this.bufferSize, 1, 1);
    
    // Create output gain (muted to prevent feedback)
    this.outputGain = this.audioContext.createGain();
    this.outputGain.gain.value = 0;  // Mute output to speakers

    // Connect nodes with enhanced audio pipeline
    this.mediaStreamSource.connect(this.gainNode);         // Boost input
    this.gainNode.connect(this.compressor);               // Apply compression
    this.compressor.connect(this.analyzerNode);           // For visualization
    this.analyzerNode.connect(this.processorNode);        // For processing
    this.processorNode.connect(this.outputGain);          // Muted output
    this.outputGain.connect(this.audioContext.destination);
    
    this.isActive = true;

    // Process audio
    this.processorNode.onaudioprocess = (event) => {
      const inputData = event.inputBuffer.getChannelData(0);
      this.processAudioData(inputData);
    };
  }

  processAudioData(inputData) {
    // Improved noise gate with dynamic threshold
    const noiseThreshold = 0.008; // Lower threshold for better voice detection
    
    // Use RMS (Root Mean Square) for better noise detection
    const rms = Math.sqrt(inputData.reduce((sum, x) => sum + x * x, 0) / inputData.length);
    
    // Convert to Int16 with noise gate and gain boost
    const int16Data = new Int16Array(inputData.length);
    for (let i = 0; i < inputData.length; i++) {
      let sample = inputData[i];
      
      // Apply noise gate
      if (Math.abs(sample) < noiseThreshold) {
        sample = 0;
      } else {
        // Boost the signal for samples above noise threshold
        sample *= 1.5; // Increase volume by 50%
      }
      
      // Clamp the values to prevent distortion
      sample = Math.max(-1, Math.min(1, sample));
      
      // Convert to 16-bit integer
      int16Data[i] = sample < 0 ? sample * 0x8000 : sample * 0x7FFF;
    }
    
    this.audioBuffer.push(...int16Data);

    // Send when we have enough data and enough time has passed
    const currentTime = Date.now();
    if (this.audioBuffer.length >= this.sampleRate * 3 && // Wait for 3 seconds of data
        !this.isProcessing && 
        currentTime - this.lastProcessTime >= this.processInterval) {
      this.isProcessing = true;
      
      try {
        // Combine overlap buffer with new data for better context
        const combinedBuffer = [...this.overlapBuffer, ...this.audioBuffer];
        
        // Use 5 seconds of audio with 2 second overlap
        const dataToSend = combinedBuffer.slice(0, this.sampleRate * 5);
        
        // Keep last 2 seconds for overlap context
        const overlapStart = Math.max(0, dataToSend.length - this.sampleRate * 2);
        this.overlapBuffer = dataToSend.slice(overlapStart);
        
        // Keep any remaining data in the buffer
        const newBufferStart = Math.min(this.audioBuffer.length, this.sampleRate * 3);
        this.audioBuffer = this.audioBuffer.slice(newBufferStart);
        
        // Only send if we have actual audio (not just silence)
        const hasAudio = dataToSend.some(sample => Math.abs(sample) > this.silenceThreshold * 0x7FFF);
        
        if (hasAudio && this.ws && this.ws.readyState === WebSocket.OPEN) {
          const buffer = new Int16Array(dataToSend).buffer;
          this.ws.send(buffer);
          this.lastProcessTime = currentTime;
        }
      } catch (error) {
        console.error('Error processing audio:', error);
      } finally {
        this.isProcessing = false;
      }
    }
  }

  async stop() {
    return new Promise(async (resolve, reject) => {
      try {
        this.isActive = false;

        // Clean up audio nodes in reverse order of connection
        const safeDisconnect = (node) => {
          if (node) {
            try {
              node.disconnect();
            } catch (e) {
              console.log('Node already disconnected');
            }
          }
        };

        // Disconnect nodes in reverse order
        safeDisconnect(this.gainNode);
        safeDisconnect(this.processorNode);
        safeDisconnect(this.analyzerNode);
        safeDisconnect(this.mediaStreamSource);

        // Clear node references
        this.gainNode = null;
        this.processorNode = null;
        this.analyzerNode = null;
        this.mediaStreamSource = null;

        // Stop media tracks
        if (this.stream) {
          this.stream.getTracks().forEach(track => {
            track.stop();
          });
          this.stream = null;
        }

        // Suspend AudioContext before closing
        if (this.audioContext && this.audioContext.state !== 'closed') {
          try {
            await this.audioContext.suspend();
            await this.audioContext.close();
          } catch (e) {
            console.log('AudioContext already closed');
          }
        }
        this.audioContext = null;

        // Handle WebSocket cleanup
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
          const closeTimeout = setTimeout(() => {
            try {
              this.ws.close();
            } catch (e) {
              console.error('Error closing WebSocket:', e);
            }
            resolve();
          }, 2000);

          this.ws.onmessage = (evt) => {
            try {
              const data = JSON.parse(evt.data);
              if (data.status === "ended") {
                clearTimeout(closeTimeout);
                this.ws.close();
                resolve();
              }
            } catch (e) {
              console.error("Error parsing final message:", e);
            }
          };

          // Send end signal to server
          this.ws.send("__END__");
        } else {
          resolve();
        }
      } catch (error) {
        console.error("Error stopping audio stream:", error);
        reject(error);
      }
    });
  }
}
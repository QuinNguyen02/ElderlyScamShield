import React, { useState, useRef, useEffect } from 'react';
import { AudioMotionVisualizer } from './AudioMotionVisualizer';
import AudioStreamer from './audioStreamer';
import './styles.css';

function App() {
  const [isStreaming, setIsStreaming] = useState(false);
  const [alert, setAlert] = useState(null);
  const [status, setStatus] = useState("Ready");
  const [monitoringTime, setMonitoringTime] = useState(0);
  const streamerRef = useRef(null);
  const timerRef = useRef(null);

  const start = async () => {
    try {
      setStatus("Initializing...");
      const wsUrl = "ws://localhost:8000/ws/stream";
      const onMessage = (data) => {
        console.log("Received from backend:", data);
        if (data.error) {
          console.error("Backend error:", data.error);
          return;
        }
        
        if (data.transcript) {
          console.log("Transcribed text:", data.transcript);
        }
        
        if (data.classification) {
          console.log("Classification result:", data.classification);
          // Show alert for high confidence scams or medium confidence with certain patterns
          if (data.classification.is_scam || data.classification.confidence > 0.5) {
            console.log("Setting alert with:", {
              text: data.transcript,
              score: data.classification.confidence,
              level: data.classification.confidence_level
            });
            setAlert({ 
              text: data.transcript, 
              score: data.classification.confidence || 0.6, // default if missing
              level: data.classification.confidence_level || 'medium'
            });
          }
        }
      };

      streamerRef.current = new AudioStreamer(wsUrl, onMessage);
      await streamerRef.current.start();
      
      setIsStreaming(true);
      setStatus("Listening...");
    } catch (error) {
      console.error("Failed to start:", error);
      setStatus("Failed to start");
    }
  };

  const stop = async () => {
    try {
      if (streamerRef.current) {
        await streamerRef.current.stop();
      }
      setIsStreaming(false);
      setStatus("Stopped");
    } catch (error) {
      console.error("Failed to stop:", error);
      setStatus("Error stopping");
    }
  };

  return (
    <div className="app-container">
      <header className="header">
        <div className="shield-icon">🛡️</div>
        <h1>Elderly Scam Shield</h1>
        <p>Protecting your loved ones from voice scams</p>
      </header>

      <div className="visualization-container">
        <AudioMotionVisualizer
          audioContext={streamerRef.current?.audioContext}
          sourceNode={streamerRef.current?.analyzerNode}
          isActive={isStreaming}
        />
      </div>

      <div className="button-container">
        <button 
          className={`monitoring-button ${isStreaming ? 'stop' : ''}`}
          onClick={isStreaming ? stop : start}
        >
          {isStreaming ? "Stop Monitoring" : "Start Monitoring"}
        </button>
        <div className="status-indicator">
          <div className={`status-dot ${isStreaming ? 'active' : ''}`}></div>
          <span>{status}</span>
        </div>
      </div>

      {alert && (
        <div className="alert-box">
          <h2>⚠️ Potential Scam Detected</h2>
          <p><strong>Transcript:</strong> {alert.text}</p>
          
          <div className="confidence-meter">
            <div 
              className="confidence-meter-fill" 
              style={{width: `${alert.score * 100}%`}}
            />
          </div>
          <p><strong>Confidence:</strong> {(alert.score * 100).toFixed(0)}%</p>
          
          <div className="alert-actions">
            <button 
              className="not-scam-btn"
              onClick={() => {
                // TODO: Send feedback
                setAlert(null);
              }}
            >
              This is NOT a scam
            </button>
            <button 
              className="share-btn"
              onClick={() => {
                if (navigator.share) {
                  navigator.share({
                    text: `Please check this suspicious call: ${alert.text}`
                  }).catch(console.error);
                } else {
                  alert("Share feature not available");
                }
              }}
            >
              Share with family
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
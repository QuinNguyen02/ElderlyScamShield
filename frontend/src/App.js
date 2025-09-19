import React, { useState, useRef, useEffect } from "react";
import { AudioMotionVisualizer } from "./AudioMotionVisualizer";
import AudioStreamer from "./audioStreamer";
import "./styles.css";

function App() {
  const [isStreaming, setIsStreaming] = useState(false);
  const [alert, setAlert] = useState(null);
  const [status, setStatus] = useState("Ready");
  const [monitoringTime, setMonitoringTime] = useState(0);
  const streamerRef = useRef(null);
  const timerRef = useRef(null);

  useEffect(() => {
    if (isStreaming) {
      timerRef.current = setInterval(() => {
        setMonitoringTime(time => time + 1);
      }, 1000);
    } else {
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
      setMonitoringTime(0);
    }
    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
    };
  }, [isStreaming]);

  const formatTime = (seconds) => {
    const hrs = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    return `${hrs.toString().padStart(2, '0')}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  const start = async () => {
    try {
      // Clear any existing alerts when starting new monitoring session
      setAlert(null);
      setStatus("Initializing...");
      const wsUrl = "ws://localhost:8000/ws/stream";
      const onMessage = (data) => {
        console.log("WS message", data);
        if (data.classification && data.classification.is_scam && data.classification.confidence > 0.6) {
          setAlert({ 
            text: data.transcript, 
            score: data.classification.confidence,
            level: data.classification.confidence_level
          });
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

      <div className="control-panel">
        <div className="status-indicator">
          <div className={`status-dot ${isStreaming ? 'active' : ''}`}></div>
          <span>{status}</span>
          {isStreaming && <div className="monitoring-time">⏱️ {formatTime(monitoringTime)}</div>}
        </div>
        
        <button 
          className={`monitoring-button ${isStreaming ? 'stop' : ''}`}
          onClick={isStreaming ? stop : start}
        >
          {isStreaming ? "Stop Monitoring" : "Start Monitoring"}
        </button>

        <div className="visualization-container">
          <AudioMotionVisualizer
            audioContext={streamerRef.current?.audioContext}
            sourceNode={streamerRef.current?.analyzerNode}
            isActive={isStreaming}
          />
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
          <p><strong>Confidence:</strong> {(alert.score * 100).toFixed(0)}% ({alert.level})</p>
          
          <div className="alert-actions">
            <button 
              className="not-scam-btn"
              onClick={async () => {
                try {
                  // Send feedback to backend
                  const response = await fetch('http://localhost:8000/feedback', {
                    method: 'POST',
                    headers: {
                      'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                      transcript: alert.text,
                      originalScore: alert.score,
                      feedback: 'not_scam',
                      timestamp: new Date().toISOString()
                    })
                  });
                  
                  if (response.ok) {
                    // Show thank you message
                    setStatus('Thank you for your feedback!');
                    setTimeout(() => setStatus('Listening...'), 3000);
                  }
                } catch (error) {
                  console.error('Failed to send feedback:', error);
                }
                // Clear the alert
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
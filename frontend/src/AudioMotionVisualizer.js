import React, { useEffect, useRef } from 'react';

export const AudioMotionVisualizer = ({ audioContext, sourceNode, isActive }) => {
  const canvasRef = useRef(null);
  const animationFrameRef = useRef(null);
  const analyzerRef = useRef(null);

  useEffect(() => {
    if (!audioContext || !sourceNode || !isActive || !canvasRef.current) {
      return;
    }

    // Create analyzer node if it doesn't exist
    if (!analyzerRef.current) {
      analyzerRef.current = audioContext.createAnalyser();
      analyzerRef.current.fftSize = 2048;
      sourceNode.connect(analyzerRef.current);
    }

    const analyzer = analyzerRef.current;
    const canvas = canvasRef.current;
    const canvasCtx = canvas.getContext('2d');
    const bufferLength = analyzer.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);

    const draw = () => {
      // Request next frame
      animationFrameRef.current = requestAnimationFrame(draw);

      // Get frequency data
      analyzer.getByteTimeDomainData(dataArray);

      // Clear canvas
      canvasCtx.fillStyle = 'rgb(200, 200, 200)';
      canvasCtx.fillRect(0, 0, canvas.width, canvas.height);

      // Draw waveform
      canvasCtx.lineWidth = 2;
      canvasCtx.strokeStyle = 'rgb(0, 123, 255)';
      canvasCtx.beginPath();

      const sliceWidth = canvas.width * 1.0 / bufferLength;
      let x = 0;

      for (let i = 0; i < bufferLength; i++) {
        const v = dataArray[i] / 128.0;
        const y = v * canvas.height / 2;

        if (i === 0) {
          canvasCtx.moveTo(x, y);
        } else {
          canvasCtx.lineTo(x, y);
        }

        x += sliceWidth;
      }

      canvasCtx.lineTo(canvas.width, canvas.height / 2);
      canvasCtx.stroke();
    };

    // Start animation
    draw();

    // Cleanup
    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
      if (analyzerRef.current) {
        try {
          sourceNode.disconnect(analyzerRef.current);
        } catch (e) {
          console.log('Node already disconnected');
        }
        analyzerRef.current = null;
      }
    };
  }, [audioContext, sourceNode, isActive]);

  return (
    <canvas 
      ref={canvasRef} 
      width={600} 
      height={200}
      style={{
        width: '100%',
        height: '200px',
        background: 'rgb(200, 200, 200)',
        borderRadius: '8px'
      }}
    />
  );
};
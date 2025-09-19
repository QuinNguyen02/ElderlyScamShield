import React, { useEffect, useRef } from 'react';
import AudioMotionAnalyzer from 'audiomotion-analyzer';

export function AudioMotionVisualizer({ audioContext, sourceNode, isActive }) {
    const containerRef = useRef(null);
    const analyzerRef = useRef(null);

    // Cleanup function
    const cleanupAnalyzer = () => {
        if (analyzerRef.current) {
            try {
                // Stop the analyzer before destroying
                analyzerRef.current.stop();
                
                // Safely disconnect any connections
                try {
                    if (sourceNode) {
                        sourceNode.disconnect();
                    }
                } catch (e) {
                    console.log('Source already disconnected');
                }
                
                // Destroy the analyzer
                analyzerRef.current.destroy();
            } catch (e) {
                console.log('Cleanup error:', e);
            }
            analyzerRef.current = null;
        }
    };

    useEffect(() => {
        if (containerRef.current && audioContext && sourceNode) {
            // Clean up any existing analyzer
            cleanupAnalyzer();

            try {
                // Create AudioMotion analyzer
                analyzerRef.current = new AudioMotionAnalyzer(containerRef.current, {
                    source: sourceNode,
                    height: 200,
                    width: containerRef.current.clientWidth,
                    mode: 5,  // "LED bars" mode
                    smoothing: 0.7,
                    gradient: 'rainbow',
                    showScaleX: false,
                    minDecibels: -70,
                    maxDecibels: -30,
                    showPeaks: true,
                    fillAlpha: 0.7,
                    useCanvas: true,
                    connectSpeakers: false  // Don't connect to speakers
                });

                // Handle resize
                const handleResize = () => {
                    if (analyzerRef.current && containerRef.current) {
                        analyzerRef.current.width = containerRef.current.clientWidth;
                    }
                };
                window.addEventListener('resize', handleResize);

                return () => {
                    window.removeEventListener('resize', handleResize);
                    cleanupAnalyzer();
                };
            } catch (e) {
                console.error('Error creating analyzer:', e);
            }
        }
        
        return () => {
            cleanupAnalyzer();
        };
    }, [audioContext, sourceNode]);

    // Update analyzer when active state changes
    useEffect(() => {
        if (analyzerRef.current) {
            if (isActive) {
                analyzerRef.current.start();
            } else {
                analyzerRef.current.stop();
            }
        }
    }, [isActive]);

    return (
        <div 
            ref={containerRef} 
            style={{ 
                width: '100%', 
                height: '200px',
                backgroundColor: '#000',
                borderRadius: '8px',
                overflow: 'hidden'
            }} 
        />
    );
}
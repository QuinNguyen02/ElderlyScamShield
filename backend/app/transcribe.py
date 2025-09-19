# backend/app/transcribe.py
import os
import whisper
_model = None

def load_whisper(model_size="small"):
    global _model
    if _model is None:
        _model = whisper.load_model(model_size)
    return _model

def verify_file_access(file_path, max_retries=5, delay=0.5):
    """Verify file exists and is accessible for reading"""
    import time
    
    for i in range(max_retries):
        try:
            if not os.path.exists(file_path):
                print(f"Attempt {i+1}: File does not exist: {file_path}")
                time.sleep(delay)
                continue
                
            # Try to open and read the file
            with open(file_path, 'rb') as f:
                # Read file header (first 44 bytes for WAV)
                header = f.read(44)
                if len(header) < 44:
                    raise ValueError("File too small to be valid WAV")
                    
                # Verify WAV header
                if header[:4] != b'RIFF' or header[8:12] != b'WAVE':
                    raise ValueError("Invalid WAV file format")
                    
                # Seek to end to verify full file is accessible
                f.seek(0, 2)
                size = f.tell()
                
                print(f"File verified: {file_path}")
                print(f"Size: {size} bytes")
                print(f"Header: RIFF={header[:4]}, WAVE={header[8:12]}")
                return True
                
        except (IOError, PermissionError) as e:
            print(f"Attempt {i+1}: Cannot access file: {e}")
            time.sleep(delay)
            continue
            
    return False

def load_audio(file_path):
    """Load audio file using soundfile to ensure it's valid"""
    import soundfile as sf
    import numpy as np
    
    print(f"Loading audio file: {file_path}")
    try:
        # Read the audio file directly
        audio_data, sample_rate = sf.read(file_path)
        
        # Convert to mono if stereo
        if len(audio_data.shape) > 1:
            audio_data = audio_data.mean(axis=1)
            
        # Normalize to float32
        audio_data = audio_data.astype(np.float32)
        
        print(f"Successfully loaded audio: shape={audio_data.shape}, sr={sample_rate}")
        return audio_data, sample_rate
        
    except Exception as e:
        print(f"Error loading audio file: {e}")
        raise

def transcribe_file(path, language=None):
    try:
        print(f"Loading Whisper model for transcription...")
        m = load_whisper("tiny")  # Using tiny for faster demo
        
        print(f"Loading audio data from: {path}")
        # Load audio data directly instead of letting Whisper load it
        audio_data, sample_rate = load_audio(path)
        
        options = {}
        if language:
            options['language'] = language
            print(f"Using language: {language}")
        
        # Use transcribe with loaded audio data
        result = m.transcribe(audio_data, **options)
        print(f"Transcription completed successfully")
        return result
        
    except Exception as e:
        print(f"Transcription error for {path}: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        raise
        
    except Exception as e:
        print(f"Transcription error for {path}: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        raise  # Re-raise the exception for proper error handling
        raise
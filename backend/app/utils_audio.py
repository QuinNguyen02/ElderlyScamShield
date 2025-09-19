# backend/app/utils_audio.py
import os
import numpy as np
import soundfile as sf

def save_bytes_to_wav(wav_bytes: bytes, wav_path: str, samplerate=16000):
    """
    Save audio bytes to a WAV file with extensive error checking and logging.
    """
    try:
        # Print input parameters
        print(f"Saving WAV file:")
        print(f"  Path: {wav_path}")
        print(f"  Bytes length: {len(wav_bytes)}")
        print(f"  Sample rate: {samplerate}")
        
        # Convert to Windows path format and ensure it's absolute
        wav_path = os.path.abspath(wav_path)
        print(f"  Absolute path: {wav_path}")
        
        # Create parent directory if it doesn't exist
        parent_dir = os.path.dirname(wav_path)
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)
            print(f"  Parent directory ready: {parent_dir}")
        
        # Convert bytes to numpy array with error checking
        try:
            audio_data = np.frombuffer(wav_bytes, dtype='int16')
            print(f"  Converted to numpy array: {audio_data.shape}")
        except Exception as e:
            raise ValueError(f"Failed to convert bytes to numpy array: {e}")
        
        # Ensure we have valid audio data
        if len(audio_data) == 0:
            raise ValueError("Empty audio data after conversion")
        
        # Write to WAV file with explicit error handling
        try:
            print("  Writing WAV file...")
            sf.write(wav_path, audio_data, samplerate, subtype='PCM_16')
            print("  WAV file written successfully")
        except Exception as e:
            raise IOError(f"Failed to write WAV file: {e}")
        
        # Verify file was written correctly
        if not os.path.exists(wav_path):
            raise FileNotFoundError(f"WAV file not found after writing: {wav_path}")
        
        file_size = os.path.getsize(wav_path)
        if file_size == 0:
            raise IOError(f"WAV file is empty after writing: {wav_path}")
        else:
            print(f"  Final file size: {file_size} bytes")
            
        return wav_path
            
    except Exception as e:
        print(f"Error in save_bytes_to_wav:")
        print(f"  Error type: {type(e).__name__}")
        print(f"  Error message: {str(e)}")
        print(f"  Target path: {wav_path}")
        # Don't remove the file on error anymore - keep it for debugging
        raise
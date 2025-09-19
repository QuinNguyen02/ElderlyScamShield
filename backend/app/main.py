# backend/app/main.py
import os, tempfile, json, time
import shutil  # for file operations
import asyncio
from fastapi import FastAPI, WebSocket, UploadFile, File, BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime

class FeedbackModel(BaseModel):
    transcript: str
    originalScore: float
    feedback: str
    timestamp: datetime
from .classifier import load_model, classify_text
from .transcribe import transcribe_file
from .utils_audio import save_bytes_to_wav

def ensure_file_exists(file_path: str, timeout: int = 5):
    """Wait for file to be fully written and accessible"""
    start_time = time.time()
    while not os.path.exists(file_path):
        if time.time() - start_time > timeout:
            raise TimeoutError(f"File not found after {timeout} seconds: {file_path}")
        time.sleep(0.1)
    
    while True:
        if time.time() - start_time > timeout:
            raise TimeoutError(f"File not stable after {timeout} seconds: {file_path}")
        try:
            with open(file_path, 'rb') as f:
                # Try to read the file to ensure it's not locked
                f.read(1)
            return True
        except (IOError, PermissionError):
            time.sleep(0.1)

def cleanup_old_files(directory: str, max_age_seconds: int = 3600):
    """Remove files older than max_age_seconds from the directory"""
    current_time = time.time()
    try:
        for filename in os.listdir(directory):
            file_path = os.path.join(directory, filename)
            if os.path.isfile(file_path):
                # Check if file is older than max_age_seconds
                if current_time - os.path.getctime(file_path) > max_age_seconds:
                    try:
                        os.remove(file_path)
                    except Exception as e:
                        print(f"Error removing old file {file_path}: {e}")
    except Exception as e:
        print(f"Error during cleanup: {e}")

# Set up directories
APP_ROOT = os.path.dirname(os.path.abspath(__file__))
AUDIO_CACHE_DIR = os.path.join(APP_ROOT, "data", "audio_cache")
MODEL_DIR = os.path.join(APP_ROOT, "..", "..", "model")
FEEDBACK_DIR = os.path.join(APP_ROOT, "data", "feedback")
BASE_DATA_PATH = os.path.join(APP_ROOT, "..", "..", "data", "train.csv")

# Initialize model training service
from .model_training import ModelTrainingService
training_service = ModelTrainingService(FEEDBACK_DIR, MODEL_DIR, BASE_DATA_PATH)

# Ensure the audio cache directory exists and is writable
try:
    os.makedirs(AUDIO_CACHE_DIR, exist_ok=True)
    # Test if directory is writable
    test_file = os.path.join(AUDIO_CACHE_DIR, "test.tmp")
    with open(test_file, "w") as f:
        f.write("test")
    os.remove(test_file)
    print(f"Audio cache directory ready at: {AUDIO_CACHE_DIR}")
except Exception as e:
    print(f"Error setting up audio cache directory: {e}")
    raise

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

MODEL = load_model()

async def check_and_retrain_model():
    """Background task to check if model needs retraining"""
    if training_service.should_retrain():
        print("Starting model retraining...")
        success = training_service.retrain_model()
        if success:
            # Reload the model
            global MODEL
            MODEL = load_model()
            print("Model successfully retrained and reloaded")
        else:
            print("Model retraining failed")

@app.post("/feedback")
async def receive_feedback(feedback: FeedbackModel, background_tasks: BackgroundTasks):
    try:
        # Store feedback in a log file for later analysis
        feedback_dir = os.path.join(APP_ROOT, "data", "feedback")
        os.makedirs(feedback_dir, exist_ok=True)
        
        feedback_file = os.path.join(feedback_dir, "feedback_log.jsonl")
        with open(feedback_file, "a") as f:
            f.write(json.dumps({
                "transcript": feedback.transcript,
                "original_score": feedback.originalScore,
                "feedback": feedback.feedback,
                "timestamp": feedback.timestamp.isoformat()
            }) + "\n")
        
        # Schedule model retraining check
        background_tasks.add_task(check_and_retrain_model)
        
        return {"status": "success", "message": "Feedback received and model update scheduled"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/classify_text")
async def classify_text_endpoint(payload: dict):
    text = payload.get("text","")
    classification = classify_text(MODEL, text)
    return JSONResponse(content=classification)

@app.post("/upload_wav")
async def upload_wav(file: UploadFile = File(...)):
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    contents = await file.read()
    tmp.write(contents)
    tmp.flush()
    tmp.close()
    r = transcribe_file(tmp.name)
    text = r.get("text","")
    classification = classify_text(MODEL, text)
    os.remove(tmp.name)
    return {
        "transcript": text,
        "classification": classification
    }

@app.websocket("/ws/stream")
async def websocket_stream(websocket: WebSocket):
    await websocket.accept()
    # collect bytes until threshold then transcribe
    buf = bytearray()
    CHUNK_BYTES = 16000 * 2 * 5  # 5s worth of 16kHz 16-bit samples
    session_id = str(int(time.time() * 1000))  # Create unique session ID
    
    # Clean up old files before starting
    cleanup_old_files(AUDIO_CACHE_DIR)
    
    try:
        while True:
            msg = await websocket.receive()
            if "bytes" in msg:
                buf.extend(msg["bytes"])
                if len(buf) >= CHUNK_BYTES:
                    # Create a WAV file in our audio cache directory
                    timestamp = int(time.time() * 1000)
                    filename = f"audio_{session_id}_{timestamp}.wav"
                    tmp_path = os.path.join(AUDIO_CACHE_DIR, filename)
                    
                    try:
                        print(f"Saving audio to: {tmp_path}")
                        
                        # Save audio data and create a backup copy
                        save_bytes_to_wav(bytes(buf), tmp_path, samplerate=16000)
                        backup_path = tmp_path + '.backup'
                        shutil.copy2(tmp_path, backup_path)
                        
                        # Ensure file is fully written and accessible
                        ensure_file_exists(tmp_path)
                        print(f"Successfully saved audio file ({os.path.getsize(tmp_path)} bytes)")
                        
                        # Process the audio
                        try:
                            print(f"Starting transcription of {tmp_path}")
                            # Ensure files are synced to disk
                            os.sync() if hasattr(os, 'sync') else None  # Sync on Unix-like systems
                            
                            # Force flush all file buffers
                            try:
                                import psutil
                                process = psutil.Process()
                                process.memory_maps()  # Force memory flush
                            except ImportError:
                                pass  # psutil not available
                                
                            # Use backup file for transcription
                            r = transcribe_file(backup_path)
                            text = r.get("text","")
                            print(f"Transcription result: {text}")
                            
                            if text and text.strip():  # Only process if we got some text
                                out = classify_text(MODEL, text)
                                print(f"Classification result: {out}")
                                response = {
                                    "transcript": text,
                                    "classification": out
                                }
                                print(f"Sending to frontend: {response}")
                                await websocket.send_text(json.dumps(response))
                        except Exception as e:
                            print(f"Error during transcription/classification: {e}")
                            print(f"Original file exists: {os.path.exists(tmp_path)}")
                            print(f"Backup file exists: {os.path.exists(backup_path)}")
                            print(f"Original file size: {os.path.getsize(tmp_path) if os.path.exists(tmp_path) else 'N/A'}")
                            print(f"Backup file size: {os.path.getsize(backup_path) if os.path.exists(backup_path) else 'N/A'}")
                            await websocket.send_text(json.dumps({
                                "error": str(e),
                                "errorType": type(e).__name__,
                                "path": tmp_path
                            }))
                            
                    except Exception as e:
                        print(f"Error in audio processing pipeline: {e}")
                        await websocket.send_text(json.dumps({
                            "error": str(e),
                            "errorType": type(e).__name__,
                            "path": tmp_path
                        }))
                    finally:
                        # Clear buffer regardless of success/failure
                        buf = bytearray()
                        
                        try:
                            # Clean up backup file if it exists
                            if os.path.exists(backup_path):
                                os.remove(backup_path)
                        except Exception as e:
                            print(f"Error cleaning up backup file: {e}")
                        
                        print(f"Audio file remains at: {tmp_path} for debugging")
            elif "text" in msg:
                txt = msg["text"]
                if txt == "__END__":
                    if buf:
                        # Use the same audio cache directory for final buffer
                        timestamp = int(time.time() * 1000)
                        filename = f"audio_{session_id}_final_{timestamp}.wav"
                        tmp_path = os.path.join(AUDIO_CACHE_DIR, filename)
                        
                        try:
                            print(f"Processing final buffer, saving to: {tmp_path}")
                            
                            # Save audio data
                            save_bytes_to_wav(bytes(buf), tmp_path, samplerate=16000)
                            
                            # Ensure file is fully written and accessible
                            ensure_file_exists(tmp_path)
                            print(f"Final buffer saved ({os.path.getsize(tmp_path)} bytes)")
                            
                            # Ensure we have write permissions and the file is accessible
                            os.chmod(tmp_path, 0o644)  # Set read permissions
                            
                            # Wait a moment for file system to catch up
                            await asyncio.sleep(0.1)
                            
                            print(f"Starting transcription of {tmp_path}")
                            # Transcribe the original file
                            r = transcribe_file(tmp_path)
                            text = r.get("text","")
                            print(f"Final transcription result: {text}")
                            
                            if text and text.strip():
                                out = classify_text(MODEL, text)
                                await websocket.send_text(json.dumps({
                                    "transcript": text,
                                    "classification": out,
                                    "final": True
                                }))
                                
                        except Exception as e:
                            print(f"Error processing final buffer: {e}")
                            print(f"Original file exists: {os.path.exists(tmp_path)}")
                            print(f"Backup file exists: {os.path.exists(backup_path)}")
                            print(f"Original file size: {os.path.getsize(tmp_path) if os.path.exists(tmp_path) else 'N/A'}")
                            print(f"Backup file size: {os.path.getsize(backup_path) if os.path.exists(backup_path) else 'N/A'}")
                            await websocket.send_text(json.dumps({
                                "error": str(e),
                                "errorType": type(e).__name__,
                                "path": tmp_path
                            }))
                            
                        finally:
                            try:
                                # Clean up backup file if it exists
                                if os.path.exists(backup_path):
                                    os.remove(backup_path)
                            except Exception as e:
                                print(f"Error cleaning up backup file: {e}")
                            
                            print(f"Final audio file remains at: {tmp_path} for debugging")
                    
                    # Send final status
                    await websocket.send_text(json.dumps({
                        "status": "ended",
                        "message": "Recording stopped successfully"
                    }))
                    await websocket.close()
                    return
                else:
                    # Allow testing by sending text directly
                    out = classify_text(MODEL, txt)
                    await websocket.send_text(json.dumps({"text": txt, "classification": out}))
    except Exception as e:
        try:
            await websocket.close()
        except:
            pass
        print("WebSocket error:", e)
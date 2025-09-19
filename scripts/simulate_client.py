# scripts/simulate_client.py
import websocket
import time
import json

def send_wav(ws_url, wav_path):
    ws = websocket.create_connection(ws_url)
    with open(wav_path, "rb") as f:
        data = f.read()
    # If server expects raw PCM16, convert WAV to PCM16 bytes before sending:
    ws.send_binary(data)
    ws.send("__END__")
    while True:
        try:
            msg = ws.recv()
            if not msg:
                break
            print("RECV:", msg)
        except Exception as e:
            print("err", e)
            break

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python simulate_client.py data/raw/scam1.wav")
    else:
        send_wav("ws://localhost:8000/ws/stream", sys.argv[1])
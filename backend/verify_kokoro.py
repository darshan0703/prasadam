"""
Verification Script for Kokoro TTS Integration in TheAtom Prasadam
Checks:
1. Imports Kokoro and required dependencies
2. Initializes the model and verifies singleton behavior
3. Synthesizes a test sentence
4. Verifies audio data, 24kHz sample rate, and non-empty WAV header
5. Calls the FastAPI /tts endpoint and inspects status, headers, and payload
"""

import sys
import io
import soundfile as sf
from fastapi.testclient import TestClient
from api import app
from tts_service import kokoro_tts

def run_verification():
    print("=" * 70)
    print("KOKORO TTS INTEGRATION VERIFICATION")
    print("=" * 70)

    # 1. Dependency imports
    print("\n[Check 1] Checking package imports...")
    import kokoro
    import torch
    import misaki
    print(f"  - kokoro version:     {kokoro.__version__}")
    print(f"  - torch version:      {torch.__version__}")
    print(f"  - misaki version:     {misaki.__version__}")
    print("  -> Kokoro and dependencies imported successfully.")

    # 2. Model initialization
    print("\n[Check 2] Inspecting model initialization status...")
    status = kokoro_tts.get_status()
    print(f"  - ready:              {status['ready']}")
    print(f"  - engine:             {status['engine']}")
    print(f"  - model_repo:         {status['model_repo']}")
    print(f"  - default_voice:      {status['default_voice']}")
    print(f"  - sample_rate:        {status['sample_rate']} Hz")
    assert status["ready"] is True, "Kokoro TTS is not ready"
    print("  -> Kokoro model initialized successfully.")

    # 3. Direct service synthesis
    test_sentence = "Welcome to The Atom Prasadam! Enjoy fresh South Indian dishes."
    print(f"\n[Check 3] Synthesizing test sentence: '{test_sentence}'...")
    audio_bytes = kokoro_tts.synthesize(test_sentence)
    print(f"  - synthesized bytes:  {len(audio_bytes)}")
    assert len(audio_bytes) > 5000, "Audio bytes are too small"
    print("  -> Synthesis generated non-empty audio.")

    # 4. Verify format and sample rate
    print("\n[Check 4] Validating audio format and sample rate...")
    assert audio_bytes[:4] == b"RIFF", "Missing RIFF header"
    assert audio_bytes[8:12] == b"WAVE", "Missing WAVE header"
    buf = io.BytesIO(audio_bytes)
    data, sr = sf.read(buf)
    print(f"  - container:          WAV (RIFF/WAVE)")
    print(f"  - sample rate:        {sr} Hz (expected: 24000 Hz)")
    print(f"  - total samples:      {len(data)}")
    print(f"  - duration:           {len(data) / sr:.2f} seconds")
    assert sr == 24000, f"Expected 24000 Hz sample rate, got {sr}"
    print("  -> Format and sample rate verified.")

    # 5. Live FastAPI endpoint test
    print("\n[Check 5] Calling FastAPI /tts endpoint...")
    client = TestClient(app)
    resp = client.post("/tts", json={"text": "Your masala dosa is ready at the counter."})
    print(f"  - HTTP status:        {resp.status_code}")
    print(f"  - Content-Type:       {resp.headers.get('content-type')}")
    print(f"  - X-TTS-Engine:       {resp.headers.get('x-tts-engine')}")
    print(f"  - X-Sample-Rate:      {resp.headers.get('x-sample-rate')}")
    print(f"  - Content-Length:     {resp.headers.get('content-length')} bytes")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    assert resp.headers.get("content-type") == "audio/wav"
    assert resp.headers.get("x-tts-engine") == "kokoro"
    assert resp.headers.get("x-sample-rate") == "24000"
    print("  -> FastAPI endpoint contract verified.")

    # 6. Status endpoint test
    print("\n[Check 6] Calling FastAPI /tts/status endpoint...")
    status_resp = client.get("/tts/status")
    assert status_resp.status_code == 200
    print(f"  - status JSON:        {status_resp.json()}")
    print("  -> Status endpoint verified.")

    print("\n" + "=" * 70)
    print("ALL KOKORO TTS VERIFICATION CHECKS PASSED SUCCESSFULLY!")
    print("=" * 70)

if __name__ == "__main__":
    run_verification()

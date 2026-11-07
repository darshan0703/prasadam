# TheAtom Prasadam — AI Restaurant Cashier Kiosk

An intelligent, voice-and-touch restaurant cashier kiosk for TheAtom Prasadam, an authentic pure vegetarian South & North Indian restaurant in Bengaluru.

## Architecture Overview

- **Backend:** FastAPI (Python 3.11), authoritative for 262 authentic dishes, 19 canonical sections, and 6 macro category groups in `menu_data.py`. Thread-safe transactional session cart, in-memory order records, idempotent checkout, and speech services (TTS & STT).
- **Frontend:** React 19 + Vite, optimized for portrait kiosk displays (1080×1920), temple-inspired dark gold/stone aesthetics, compact header with Voice AI assistant modal, stepper controls, real-time cart dock, and checkout.
- **Conversational Engine (`conversation_service.py`):**
  - Canonical grounding in 262 authentic items from `menu_data.py` (zero invented dishes or prices).
  - Kannada natural language understanding (e.g., *"Ondu masala dosa kodi"*, numerals, action verbs).
  - Multi-turn contextual dialogue with anaphora resolution (*"Which one is cheaper?"* -> *"Add that one"* -> *"Make that two"* -> *"No, I meant one"* -> *"Remove the last item"* -> *"Cancel that"*).
  - Intelligent, authentic product recommendations based on cart contents and house specialties (Filter Coffee, Mysore Pak, Masala Dosa).
  - Dedicated Jain dietary filtering (*"Can I get that without onion?"* -> routes to `north_indian_jain_items`).
  - Zero external dependency requirement: functions 100% offline with zero cloud API keys configured. When `GEMINI_API_KEY` or `GROQ_API_KEY` is provided, enhances natural language understanding with cloud LLMs.

---

## Quick Startup Commands (For Tomorrow Morning)

### 1. Start the Backend Server (Port 8000)
```bash
cd /Users/pavan/Downloads/Theatom-prasadam
backend/venv/bin/uvicorn api:app --host 127.0.0.1 --port 8000 --app-dir backend
```
Verify running: `curl http://127.0.0.1:8000/health` -> `{"status":"running","service":"prasadam-kiosk-backend"}`

### 2. Start the Frontend Dev Server (Port 5173)
```bash
cd /Users/pavan/Downloads/Theatom-prasadam/frontend
npm run dev -- --host 127.0.0.1
```
The kiosk interface is accessible at: `http://127.0.0.1:5173`

---

## Running Verification Tests

### 1. Run Backend Unit & Integration Tests (44 tests)
```bash
cd /Users/pavan/Downloads/Theatom-prasadam
backend/venv/bin/pytest backend/test_api.py -v
```

### 2. Run Frontend Unit Tests (47 tests across 7 suites)
```bash
cd /Users/pavan/Downloads/Theatom-prasadam/frontend
npm test -- --run
```

### 3. Run Live 12-Step Full-Stack Customer Journey Audit
With both servers running (or in background):
```bash
cd /Users/pavan/Downloads/Theatom-prasadam
backend/venv/bin/python3 backend/test_live_customer_journey.py
```

### 4. Run Frontend Production Bundle Build
```bash
cd /Users/pavan/Downloads/Theatom-prasadam/frontend
npm run build
```

---

## Configuration & Environment Variables

See `backend/.env.example`.

| Variable | Required | Default | Description |
|---|---|---|---|
| `GEMINI_API_KEY` | No | None | Google Gemini REST API key for conversational enhancement. |
| `GROQ_API_KEY` | No | None | Groq API key (alternative cloud LLM provider). |
| `GROQ_MODEL` | No | `llama-3.1-8b-instant` | Groq model identifier. |
| `HOST` | No | `127.0.0.1` | Backend host. |
| `PORT` | No | `8000` | Backend port. |

### Offline / Cloud Independence
- **No API keys needed:** The kiosk's semantic intent parser in `conversation_service.py` handles 100% of ordering, item lookups, cart mutations, Kannada phrasing, price comparisons, and checkout completely offline.
- **Speech Synthesis (TTS):** macOS native `say` utility combined with `ffmpeg` generates pristine 24kHz mono WAV audio locally in <50ms without external cloud services.
- **Speech Recognition (STT):** Local Web Speech API preview in modern browsers backed by Whisper CLI conversion fallback on `/stt`.

---

## Troubleshooting Guide

### 1. Microphone Permission Errors in Browser
- If the browser displays *"Microphone permission denied"*:
  1. Click the lock/settings icon in the browser address bar for `http://localhost:5173`.
  2. Set **Microphone** to **Allow**.
  3. Reload the kiosk page.
- In automated testing or headless environments where microphone hardware is absent, the Voice Assistant modal provides an interactive typed message input and 6 pre-configured suggestion chips (*"Add Masala Dosa"*, *"Filter Coffee"*, *"Show Sweets"*, *"Pure Veg Info"*, *"Check Tray"*, *"Checkout"*) that exercise the exact same conversation engine.

### 2. Audio Playback Mute
- Tap the speaker icon in the top right of the Voice Assistant modal to toggle speech synthesis audio on/off.

### 3. Restarting In-Memory State
- Carts and order numbers (`#P-XXXX`) are held in memory during the active backend server process. Restarting the backend server clears active in-memory carts and orders by design for this kiosk demonstration.

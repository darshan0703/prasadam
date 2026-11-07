"""
Dual-Engine Text-to-Speech (TTS) Service for TheAtom Prasadam
=============================================================
Supports:
1. Pure Kannada & Code-Mixed Kannada: Native macOS 'Soumya' (kn_IN) neural voice
   via high-performance offline synthesis, resampled via ffmpeg to 24,000 Hz 16-bit mono WAV.
2. English / International: Kokoro-82M KPipeline neural TTS (24,000 Hz 16-bit mono WAV).

Features:
- Automatic language routing: Inspects text for Kannada Unicode characters (\u0C80-\u0CFF).
- Thread-safe audio generation protected by mutex locks.
- Automatic currency/text normalization for both Kannada and English.
- Identical 24 kHz mono WAV format for seamless browser playback.
"""

import os
import io
import re
import shutil
import logging
import threading
import tempfile
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any, List
import numpy as np
import soundfile as sf

logger = logging.getLogger("prasadam.tts")
logging.basicConfig(level=logging.INFO)

try:
    from kokoro import KPipeline
except ImportError:
    KPipeline = None


class DualLanguageTTSService:
    """
    Unified dual-language TTS service managing both Kokoro-82M (English)
    and native Kannada (Soumya) synthesis to 24 kHz mono WAV.
    """

    SUPPORTED_VOICES: List[str] = [
        "af_heart",   # Default American Female (warm, natural)
        "af_bella",   # American Female (expressive)
        "af_nicole",  # American Female (whispery/soft)
        "af_sarah",   # American Female
        "af_sky",     # American Female
        "am_adam",    # American Male
        "am_michael", # American Male
        "bf_emma",    # British Female
        "bf_isabella",# British Female
        "bm_george",  # British Male
        "bm_lewis",   # British Male
    ]

    def __init__(
        self,
        lang_code: Optional[str] = None,
        default_voice: Optional[str] = None,
        repo_id: str = "hexgrad/Kokoro-82M",
        auto_init: bool = True,
    ):
        self.lang_code = lang_code or os.getenv("KOKORO_LANG", "a")
        self.default_voice = default_voice or os.getenv("KOKORO_VOICE", "af_heart")
        self.repo_id = repo_id
        self.sample_rate = 24000
        self.pipeline: Optional[Any] = None
        self._kokoro_lock = threading.Lock()
        self._kannada_lock = threading.Lock()
        self._init_error: Optional[str] = None
        self._is_initialized = False

        # System binaries
        self.say_bin = shutil.which("say") or "/usr/bin/say"
        self.ffmpeg_bin = shutil.which("ffmpeg") or "/Users/pavan/.local/bin/ffmpeg"
        self.kannada_voice = os.getenv("KANNADA_VOICE", "Soumya")

        if auto_init:
            self.initialize()

    def initialize(self) -> bool:
        """Loads the Kokoro KPipeline model into memory once."""
        if self._is_initialized and self.pipeline is not None:
            return True

        with self._kokoro_lock:
            if self._is_initialized and self.pipeline is not None:
                return True

            logger.info("Initializing Kokoro TTS (lang_code=%s, repo_id=%s)...", self.lang_code, self.repo_id)
            if KPipeline is None:
                self._init_error = "kokoro package is not installed."
                logger.error("Kokoro TTS initialization failed: %s", self._init_error)
                return False

            try:
                self.pipeline = KPipeline(
                    lang_code=self.lang_code,
                    repo_id=self.repo_id,
                )
                self._is_initialized = True
                self._init_error = None
                logger.info(
                    "Kokoro TTS initialized! (Voice: %s, Rate: %d Hz). Kannada voice: %s (%s)",
                    self.default_voice,
                    self.sample_rate,
                    self.kannada_voice,
                    "available" if os.path.exists(self.say_bin) else "unavailable"
                )
                return True
            except Exception as e:
                self._init_error = f"Kokoro model load error: {repr(e)}"
                logger.error("Kokoro TTS initialization error: %s", self._init_error, exc_info=True)
                return False

    def is_ready(self) -> bool:
        """Checks if speech engines are available."""
        return self._is_initialized and self.pipeline is not None

    def has_kannada_script(self, text: str) -> bool:
        """Checks if the text contains Kannada Unicode characters (\u0C80-\u0CFF)."""
        if not text:
            return False
        return bool(re.search(r"[\u0C80-\u0CFF]", text))

    def clean_text_for_english(self, text: str) -> str:
        """Prepares English text for Kokoro phonemizer."""
        if not text:
            return ""
        cleaned = text.strip()
        cleaned = re.sub(r"₹\s*(\d+(?:\.\d+)?)", r"\1 rupees", cleaned)
        cleaned = re.sub(r"(?:Rs\.?|INR)\s*(\d+(?:\.\d+)?)", r"\1 rupees", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"₹", " rupees", cleaned)
        cleaned = re.sub(r"[\u0C80-\u0CFF]", "", cleaned)  # Strip Kannada characters
        cleaned = re.sub(r"[*_~`#\[\](){}\"\<\>]", " ", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned

    def clean_text_for_kannada(self, text: str) -> str:
        """Prepares Kannada or code-mixed text for speech synthesis."""
        if not text:
            return ""
        cleaned = text.strip()
        # Normalize rupee currency to Kannada word 'ರೂಪಾಯಿ'
        cleaned = re.sub(r"₹\s*(\d+(?:\.\d+)?)", r"\1 ರೂಪಾಯಿ", cleaned)
        cleaned = re.sub(r"(?:Rs\.?|INR)\s*(\d+(?:\.\d+)?)", r"\1 ರೂಪಾಯಿ", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"₹", " ರೂಪಾಯಿ", cleaned)
        # Remove markdown symbols and brackets
        cleaned = re.sub(r"[*_~`#\[\](){}\"\<\>]", " ", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned

    def synthesize_kannada(self, text: str) -> bytes:
        """
        Synthesizes Kannada or code-mixed speech using native macOS 'Soumya' voice
        resampled via ffmpeg to 24,000 Hz 16-bit mono WAV.
        """
        clean_text = self.clean_text_for_kannada(text)
        if not clean_text:
            clean_text = "ಸರಿ."

        with self._kannada_lock:
            with tempfile.TemporaryDirectory() as td:
                aiff_path = Path(td) / "kannada_raw.aiff"
                wav_path = Path(td) / "kannada_24k.wav"

                # Step 1: Synthesize using macOS say
                say_cmd = [self.say_bin, "-v", self.kannada_voice, "-o", str(aiff_path), clean_text]
                logger.info("Generating Kannada audio with %s: '%s'", self.kannada_voice, clean_text[:60])
                res = subprocess.run(say_cmd, capture_output=True, text=True, timeout=10)
                if res.returncode != 0 or not aiff_path.exists():
                    raise RuntimeError(f"macOS say failed: {res.stderr or res.stdout}")

                # Step 2: Resample via ffmpeg to 24,000 Hz 16-bit mono WAV
                ffmpeg_cmd = [
                    self.ffmpeg_bin, "-y", "-i", str(aiff_path),
                    "-ar", "24000", "-ac", "1", "-c:a", "pcm_s16le", str(wav_path)
                ]
                ff_res = subprocess.run(ffmpeg_cmd, capture_output=True, text=True, timeout=10)
                if ff_res.returncode != 0 or not wav_path.exists():
                    raise RuntimeError(f"ffmpeg conversion failed: {ff_res.stderr}")

                audio_bytes = wav_path.read_bytes()
                logger.info("Kannada audio synthesized: %d bytes (24 kHz mono WAV)", len(audio_bytes))
                return audio_bytes

    def synthesize_english(
        self,
        text: str,
        voice: Optional[str] = None,
        speed: float = 1.0,
    ) -> bytes:
        """Synthesizes English text using Kokoro-82M."""
        if not self.is_ready():
            if not self.initialize():
                raise RuntimeError(f"Kokoro TTS is not ready: {self._init_error or 'Unknown initialization error'}")

        clean_text = self.clean_text_for_english(text)
        if not clean_text:
            clean_text = "Prasadam order updated."

        target_voice = voice or self.default_voice

        with self._kokoro_lock:
            try:
                logger.info("Generating Kokoro audio with voice '%s': '%s'", target_voice, clean_text[:60])
                generator = self.pipeline(
                    clean_text,
                    voice=target_voice,
                    speed=speed,
                )

                audio_segments = []
                for _, _, audio in generator:
                    if audio is not None:
                        audio_segments.append(np.asarray(audio, dtype=np.float32))

                if not audio_segments:
                    raise RuntimeError("Kokoro TTS generated empty audio segments.")

                audio_data = np.concatenate(audio_segments)
                if len(audio_data) == 0:
                    raise RuntimeError("Kokoro audio data is 0 samples.")

                # Encode to 24 kHz mono WAV buffer
                buf = io.BytesIO()
                sf.write(buf, audio_data, self.sample_rate, format="WAV")
                buf.seek(0)
                audio_bytes = buf.read()

                logger.info(
                    "Kokoro audio generated successfully: %d samples, %d bytes (%.2fs)",
                    len(audio_data),
                    len(audio_bytes),
                    len(audio_data) / self.sample_rate,
                )
                return audio_bytes

            except Exception as e:
                logger.error("Kokoro synthesis error: %s", repr(e), exc_info=True)
                raise RuntimeError(f"Kokoro synthesis failed: {e}") from e

    def synthesize(
        self,
        text: str,
        voice: Optional[str] = None,
        speed: float = 1.0,
    ) -> bytes:
        """
        Unified synthesis router:
        If text contains Kannada Unicode characters, routes to native Kannada (Soumya).
        Otherwise routes to Kokoro-82M.
        Always returns 24 kHz mono WAV bytes.
        """
        if not text or not text.strip():
            raise ValueError("Text for speech synthesis cannot be empty.")

        if self.has_kannada_script(text):
            return self.synthesize_kannada(text)
        else:
            return self.synthesize_english(text, voice=voice, speed=speed)

    def synthesize_with_metadata(
        self,
        text: str,
        voice: Optional[str] = None,
        speed: float = 1.0,
    ) -> Dict[str, Any]:
        """Synthesizes text and returns audio bytes with engine metadata."""
        if not text or not text.strip():
            raise ValueError("Text for speech synthesis cannot be empty.")

        is_kannada = self.has_kannada_script(text)
        if is_kannada:
            audio_bytes = self.synthesize_kannada(text)
            engine = "kannada-soumya"
            lang = "kn"
        else:
            audio_bytes = self.synthesize_english(text, voice=voice, speed=speed)
            engine = "kokoro"
            lang = "en"

        return {
            "audio_bytes": audio_bytes,
            "engine": engine,
            "lang": lang,
            "sample_rate": self.sample_rate,
        }

    def get_status(self) -> Dict[str, Any]:
        """Returns diagnostic details about both TTS engines."""
        return {
            "ready": self.is_ready(),
            "engine": "kokoro",
            "sample_rate": self.sample_rate,
            "default_voice": self.default_voice,
            "supported_voices": self.SUPPORTED_VOICES,
            "engines": {
                "english": {
                    "engine": "kokoro",
                    "model_repo": self.repo_id,
                    "lang_code": self.lang_code,
                    "default_voice": self.default_voice,
                    "supported_voices": self.SUPPORTED_VOICES,
                    "sample_rate": self.sample_rate,
                    "ready": self._is_initialized and self.pipeline is not None,
                    "error": self._init_error,
                },
                "kannada": {
                    "engine": "kannada-soumya",
                    "voice": self.kannada_voice,
                    "sample_rate": self.sample_rate,
                    "ready": os.path.exists(self.say_bin) and os.path.exists(self.ffmpeg_bin),
                }
            }
        }


# Maintain backward compatibility alias
KokoroTTSService = DualLanguageTTSService

# Global singleton instance
kokoro_tts = DualLanguageTTSService(auto_init=True)

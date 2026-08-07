import os
import sys
import json
import wave
import struct
import math
import asyncio
import logging
import requests
from pathlib import Path
from typing import List, Dict, Any, Optional

import edge_tts

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("voice_generator")

ELEVENLABS_VOICES = [
    # Voicebox (Kokoro-82M Ultra-Realistic Neural Voices)
    {"id": "kokoro-af_heart", "name": "Heart — Voicebox Kokoro (US Female, Ultra-Realistic)", "gender": "Female"},
    {"id": "kokoro-am_adam", "name": "Adam — Voicebox Kokoro (US Male, Ultra-Realistic)", "gender": "Male"},
    {"id": "kokoro-af_bella", "name": "Bella — Voicebox Kokoro (US Female, Ultra-Realistic)", "gender": "Female"},
    {"id": "kokoro-am_michael", "name": "Michael — Voicebox Kokoro (US Male, Ultra-Realistic)", "gender": "Male"},
    {"id": "kokoro-bf_emma", "name": "Emma — Voicebox Kokoro (UK Female, Ultra-Realistic)", "gender": "Female"},
    
    # Microsoft Neural Voices
    {"id": "en-US-GuyNeural", "name": "Guy — Microsoft Neural (US Male, Free)", "gender": "Male"},
    {"id": "en-US-JennyNeural", "name": "Jenny — Microsoft Neural (US Female, Free)", "gender": "Female"},
    {"id": "en-US-AriaNeural", "name": "Aria — Microsoft Neural (US Female, Free)", "gender": "Female"},
    {"id": "en-GB-RyanNeural", "name": "Ryan — Microsoft Neural (UK Male, Free)", "gender": "Male"},
    
    # ElevenLabs API Voices
    {"id": "21m00Tcm4TlvDq8ikWAM", "name": "Rachel — ElevenLabs (US Female, API Key Required)", "gender": "Female"},
    {"id": "pNInz6obpgDQGcFmaJgB", "name": "Adam — ElevenLabs (US Male, API Key Required)", "gender": "Male"}
]

def generate_fallback_wav(duration_sec: float, output_path: str):
    """Generate a clean audio WAV file with subtle pleasant background tone."""
    sample_rate = 22050
    num_samples = int(sample_rate * duration_sec)
    
    with wave.open(output_path, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        
        for i in range(num_samples):
            t = float(i) / sample_rate
            val = int(1000 * math.sin(2.0 * math.pi * 440.0 * t) * math.exp(-t * 0.1))
            data = struct.pack('<h', val)
            wav_file.writeframesraw(data)

class VoiceoverGenerator:
    """
    Phase 2: Script -> Voiceover Audio Synthesizer.
    Supports Voicebox (Kokoro), ElevenLabs API, and Edge-TTS Neural Engines.
    """
    
    def __init__(self, elevenlabs_api_key: Optional[str] = None):
        self.api_key = elevenlabs_api_key or os.getenv("ELEVENLABS_API_KEY")
        self.samples_dir = Path(__file__).resolve().parent.parent / "output" / "voice_samples"
        self.samples_dir.mkdir(parents=True, exist_ok=True)

    def generate_sample_preview_if_missing(self, voice_info: Dict[str, str]) -> str:
        """Generate a clean 3-second voice preview sample file if missing."""
        voice_id = voice_info["id"]
        voice_name = voice_info["name"].split("—")[0].strip()
        sample_filename = f"sample_{voice_id.replace('-', '_')}.mp3"
        sample_path = self.samples_dir / sample_filename

        if not sample_path.exists() or sample_path.stat().st_size < 500:
            try:
                from backend.tts_engine import EdgeTTSEngine
                engine = EdgeTTSEngine(voice=voice_id)
                sample_text = f"Hello! I am {voice_name}, your Voicebox AI presenter."
                engine.synthesize(sample_text, str(sample_path))
            except Exception as e:
                logger.warning(f"Could not pre-generate sample preview for {voice_id}: {e}")

        return f"/output/voice_samples/{sample_filename}"

    def get_available_voices(self) -> List[Dict[str, str]]:
        voices_with_samples = []
        for v in ELEVENLABS_VOICES:
            v_copy = dict(v)
            v_copy["sample_url"] = self.generate_sample_preview_if_missing(v)
            voices_with_samples.append(v_copy)
        return voices_with_samples

    def generate_elevenlabs_audio(self, text: str, voice_id: str, output_path: str) -> (bool, str):
        """Call ElevenLabs API to generate TTS audio."""
        if not self.api_key:
            return False, "ElevenLabs API Key is missing. Please click 'API Keys' in the top right to configure your key."

        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": self.api_key
        }
        payload = {
            "text": text,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75,
                "style": 0.0,
                "use_speaker_boost": True
            }
        }

        try:
            logger.info(f"Requesting ElevenLabs TTS for voice_id: {voice_id}")
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            if response.status_code == 200:
                with open(output_path, "wb") as f:
                    f.write(response.content)
                logger.info(f"ElevenLabs audio saved successfully to {output_path}")
                return True, ""
            elif response.status_code == 401:
                return False, "ElevenLabs API Error: Invalid API Key (HTTP 401). Please check your ElevenLabs API key in Settings."
            elif response.status_code == 429:
                return False, "ElevenLabs API Error: Rate Limit / Quota Exceeded (HTTP 429). Please check your ElevenLabs character balance."
            else:
                return False, f"ElevenLabs API Error (HTTP {response.status_code}): {response.text}"
        except Exception as e:
            return False, f"Error connecting to ElevenLabs API: {str(e)}"

    def synthesize_script(
        self,
        script_segments: List[Dict[str, Any]],
        output_dir: str,
        voice_id: str = "kokoro-af_heart",
        total_video_duration: float = 0.0
    ) -> Dict[str, Any]:
        """
        Synthesize audio using Kokoro Voicebox / ElevenLabs / EdgeTTS.
        """
        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)

        full_text = " ".join([seg.get("narration", "") for seg in script_segments if seg.get("narration")])
        if not full_text.strip():
            raise ValueError("Script is empty. Cannot synthesize voiceover audio.")

        combined_audio_path = str(out_path / "combined_voiceover.mp3")

        selected_voice = voice_id if voice_id else "kokoro-af_heart"

        # Try ElevenLabs if API key is provided and non-kokoro/non-edge voice requested
        if self.api_key and not selected_voice.startswith("kokoro-") and not selected_voice.startswith("en-"):
            success, err_msg = self.generate_elevenlabs_audio(full_text, selected_voice, combined_audio_path)
            if success:
                return {
                    "status": "success",
                    "engine": "ElevenLabs API",
                    "voice_id": selected_voice,
                    "full_text": full_text,
                    "combined_audio_path": combined_audio_path,
                    "segments": []
                }
            logger.warning(f"ElevenLabs synthesis failed: {err_msg}. Falling back to Neural TTS...")

        # Free Neural Engine (Kokoro Voicebox / edge-tts with duration matching)
        try:
            from backend.tts_engine import EdgeTTSEngine
            engine = EdgeTTSEngine(voice=selected_voice)
            audio_files, engine_used_name = engine.synthesize_segments(script_segments, str(out_path))

            if audio_files:
                concat_ok = engine.concatenate_segments(audio_files, script_segments, combined_audio_path, total_video_duration=total_video_duration)
                if concat_ok and os.path.exists(combined_audio_path):
                    logger.info(f"Successfully generated voiceover via {engine_used_name}")
                    return {
                        "status": "success",
                        "engine": engine_used_name,
                        "voice_id": selected_voice,
                        "full_text": full_text,
                        "combined_audio_path": combined_audio_path,
                        "segments": audio_files
                    }

            raise RuntimeError("TTS failed to synthesize audio segments.")
        except Exception as e:
            logger.error(f"Fallback TTS failed: {e}")
            raise RuntimeError(f"Voiceover generation failed: {e}")

if __name__ == "__main__":
    vg = VoiceoverGenerator()
    test_script = [
        {"segment_id": 1, "narration": "Welcome to Navik Labs automated video narrator.", "start_time": 0, "end_time": 5},
        {"segment_id": 2, "narration": "This pipeline turns slide decks into professional voiceover videos.", "start_time": 5, "end_time": 10}
    ]
    res = vg.synthesize_script(test_script, "./test_output")
    print(res)

import os
import logging
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional

import imageio_ffmpeg

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("audio_analyzer")

def get_ffmpeg_path() -> str:
    try:
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "ffmpeg"

class AudioAnalyzer:
    """
    Extracts and transcribes spoken audio from uploaded videos.
    Supports local SpeechRecognition and fallback transcription.
    """
    def __init__(self, video_path: str):
        self.video_path = Path(video_path)
        self.ffmpeg_path = get_ffmpeg_path()

    def has_audio_stream(self) -> bool:
        """Check if video file actually contains an audio stream."""
        try:
            ffprobe_exe = self.ffmpeg_path.replace("ffmpeg.exe", "ffprobe.exe")
            if not os.path.exists(ffprobe_exe):
                ffprobe_exe = "ffprobe"
            cmd = [ffprobe_exe, "-v", "error", "-show_entries", "stream=codec_type", "-of", "csv=p=0", str(self.video_path)]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            return "audio" in res.stdout.lower()
        except Exception:
            return False

    def extract_audio_wav(self, output_wav_path: Optional[str] = None) -> Optional[str]:
        """Extract 16kHz mono WAV audio track from video file."""
        if not self.has_audio_stream():
            logger.info(f"Video {self.video_path.name} is silent (no audio stream). Skipping audio extraction.")
            return None

        if not output_wav_path:
            output_wav_path = str(self.video_path.parent / f"{self.video_path.stem}_audio.wav")
            
        cmd = [
            self.ffmpeg_path, "-y",
            "-i", str(self.video_path),
            "-vn",
            "-acodec", "pcm_s16le",
            "-ar", "16000",
            "-ac", "1",
            output_wav_path
        ]
        
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if res.returncode == 0 and os.path.exists(output_wav_path) and os.path.getsize(output_wav_path) > 1000:
                logger.info(f"Audio extracted successfully to {output_wav_path}")
                return output_wav_path
            else:
                return None
        except Exception as e:
            logger.warning(f"Failed to extract audio from {self.video_path}: {e}")
            return None

    def transcribe(self) -> Dict[str, Any]:
        """Transcribe extracted audio track."""
        if not self.has_audio_stream():
            return {"has_audio": False, "transcript": "", "notice": "Video file is silent (no audio track)."}

        wav_path = self.extract_audio_wav()
        if not wav_path:
            return {"has_audio": False, "transcript": "", "error": "Could not extract audio track"}

        try:
            import speech_recognition as sr
            r = sr.Recognizer()
            with sr.AudioFile(wav_path) as source:
                # Limit recording to maximum 30 seconds to prevent Google STT API timeouts
                audio_data = r.record(source, duration=30)
                
            try:
                text = r.recognize_google(audio_data)
                logger.info(f"Audio transcription successful: '{text[:100]}...'")
                return {
                    "has_audio": True,
                    "transcript": text,
                    "engine": "google_stt"
                }
            except Exception as stt_err:
                logger.info(f"Google STT notice: {stt_err}")
                return {
                    "has_audio": True,
                    "transcript": "",
                    "notice": "Audio track detected but no clear spoken dialogue transcribed."
                }
        except Exception as e:
            logger.warning(f"Audio analyzer error: {e}")
            return {"has_audio": False, "transcript": "", "error": str(e)}

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        aa = AudioAnalyzer(sys.argv[1])
        print(aa.transcribe())

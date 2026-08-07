"""
EdgeTTS / Kokoro Voicebox Pluggable Adapter Module.
"""
from typing import Tuple, Dict, Any, List
from backend.tts_engine import EdgeTTSEngine
from backend.pipeline.tts.base import BaseTTSEngine

class EdgeTTSAdapter(BaseTTSEngine):

    def __init__(self, voice: str = "kokoro-am_adam"):
        self.engine = EdgeTTSEngine(voice=voice)

    def synthesize(self, text: str, output_path: str) -> Tuple[bool, str]:
        return self.engine.synthesize(text, output_path)

    def get_available_voices(self) -> List[Dict[str, Any]]:
        return self.engine.get_voices()

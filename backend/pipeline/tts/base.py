"""
Base Class for Pluggable Multi-Engine TTS Adapters.
Allows hot-swappable TTS providers without changing core pipeline business logic.
"""
from abc import ABC, abstractmethod
from typing import Tuple, Dict, Any, List

class BaseTTSEngine(ABC):
    """Abstract Base Class for all TTS Engine Adapters."""

    @abstractmethod
    def synthesize(self, text: str, output_path: str) -> Tuple[bool, str]:
        """Synthesize text to audio file. Returns (success, engine_name)."""
        pass

    @abstractmethod
    def get_available_voices(self) -> List[Dict[str, Any]]:
        """Returns list of supported voices with metadata."""
        pass

import os
import json
import base64
import hashlib
import logging
from pathlib import Path
from typing import Dict, Optional, Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("credentials_manager")

BASE_DIR = Path(__file__).resolve().parent.parent
ENCRYPTED_KEYS_FILE = BASE_DIR / ".encrypted_keys.json"

def _get_machine_secret() -> bytes:
    """Generate a stable machine-specific encryption key based on environment & hostname."""
    import platform
    import getpass
    raw_id = f"NavikVoiceover_{platform.node()}_{getpass.getuser()}_SecretKey_2026"
    return hashlib.sha256(raw_id.encode('utf-8')).digest()

def _xor_cipher(data_bytes: bytes, key_bytes: bytes) -> bytes:
    """Fast XOR cipher using SHA256 machine secret key."""
    return bytes([b ^ key_bytes[i % len(key_bytes)] for i, b in enumerate(data_bytes)])

def encrypt_string(plaintext: str) -> str:
    """Encrypt plaintext string using machine key and encode to Base64."""
    if not plaintext:
        return ""
    key = _get_machine_secret()
    encrypted_bytes = _xor_cipher(plaintext.encode('utf-8'), key)
    return base64.urlsafe_b64encode(encrypted_bytes).decode('utf-8')

def decrypt_string(ciphertext: str) -> str:
    """Decrypt Base64 ciphertext using machine key back to original string."""
    if not ciphertext:
        return ""
    try:
        key = _get_machine_secret()
        encrypted_bytes = base64.urlsafe_b64decode(ciphertext.encode('utf-8'))
        decrypted_bytes = _xor_cipher(encrypted_bytes, key)
        return decrypted_bytes.decode('utf-8')
    except Exception as e:
        logger.error(f"Error decrypting credentials: {e}")
        return ""

def mask_key(key: str) -> str:
    """Produce a safe visual mask for UI display (e.g., 'xi-ap••••8a2f')."""
    if not key:
        return ""
    if len(key) <= 8:
        return "••••••••"
    return f"{key[:5]}••••••••{key[-4:]}"

class CredentialsManager:
    """
    Manages persistent, encrypted storage of API credentials.
    Keys are stored in encrypted format on disk and never exposed in logs.
    """

    def __init__(self):
        self.elevenlabs_key = ""
        self.gemini_key = ""
        self.groq_key = ""
        self._load_from_disk()

    def _load_from_disk(self):
        env_11 = os.getenv("ELEVENLABS_API_KEY", "")
        env_gem = os.getenv("GEMINI_API_KEY", "")
        env_groq = os.getenv("GROQ_API_KEY", "")
        if env_11:
            self.elevenlabs_key = env_11
        if env_gem:
            self.gemini_key = env_gem
        if env_groq:
            self.groq_key = env_groq

        if ENCRYPTED_KEYS_FILE.exists():
            try:
                with open(ENCRYPTED_KEYS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    enc_11 = data.get("elevenlabs_api_key_enc", "")
                    enc_gem = data.get("gemini_api_key_enc", "")
                    enc_groq = data.get("groq_api_key_enc", "")

                    if enc_11:
                        dec_11 = decrypt_string(enc_11)
                        if dec_11:
                            self.elevenlabs_key = dec_11
                            os.environ["ELEVENLABS_API_KEY"] = dec_11

                    if enc_gem:
                        dec_gem = decrypt_string(enc_gem)
                        if dec_gem:
                            self.gemini_key = dec_gem
                            os.environ["GEMINI_API_KEY"] = dec_gem

                    if enc_groq:
                        dec_groq = decrypt_string(enc_groq)
                        if dec_groq:
                            self.groq_key = dec_groq
                            os.environ["GROQ_API_KEY"] = dec_groq

            except Exception as e:
                logger.error(f"Error reading encrypted keys file: {e}")

    def save_keys(self, elevenlabs_key: Optional[str] = None, gemini_key: Optional[str] = None, groq_key: Optional[str] = None) -> Dict[str, Any]:
        """Encrypt and save provided keys to disk persistently."""
        if elevenlabs_key is not None:
            val = elevenlabs_key.strip()
            if val and "••••" not in val:
                self.elevenlabs_key = val
                os.environ["ELEVENLABS_API_KEY"] = val

        if gemini_key is not None:
            val = gemini_key.strip()
            if val and "••••" not in val:
                self.gemini_key = val
                os.environ["GEMINI_API_KEY"] = val

        if groq_key is not None:
            val = groq_key.strip()
            if val and "••••" not in val:
                self.groq_key = val
                os.environ["GROQ_API_KEY"] = val

        enc_11 = encrypt_string(self.elevenlabs_key)
        enc_gem = encrypt_string(self.gemini_key)
        enc_groq = encrypt_string(self.groq_key)

        data = {
            "elevenlabs_api_key_enc": enc_11,
            "gemini_api_key_enc": enc_gem,
            "groq_api_key_enc": enc_groq
        }

        with open(ENCRYPTED_KEYS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        logger.info("API Keys encrypted and saved successfully to disk.")
        return self.get_masked_status()

    def get_masked_status(self) -> Dict[str, Any]:
        """Return masked key strings and status flags for frontend display."""
        return {
            "has_elevenlabs": bool(self.elevenlabs_key),
            "has_gemini": bool(self.gemini_key),
            "has_groq": bool(self.groq_key),
            "elevenlabs_masked": mask_key(self.elevenlabs_key),
            "gemini_masked": mask_key(self.gemini_key),
            "groq_masked": mask_key(self.groq_key)
        }

    def get_elevenlabs_key(self) -> str:
        return self.elevenlabs_key

    def get_gemini_key(self) -> str:
        return self.gemini_key

    def get_groq_key(self) -> str:
        return self.groq_key

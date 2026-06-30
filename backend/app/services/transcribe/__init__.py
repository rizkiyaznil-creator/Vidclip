"""Modul transkripsi (pluggable). Mendukung OpenAI & Groq (BYOK)."""

from app.services.transcribe.base import Transcript, TranscriptWord
from app.services.transcribe.openai_compatible import transcribe_openai_compatible

__all__ = ["Transcript", "TranscriptWord", "get_transcriber", "ENGINES"]

# Konfigurasi engine: nama → (base_url, model). base_url None = default OpenAI.
ENGINES: dict[str, tuple[str | None, str]] = {
    "openai": (None, "whisper-1"),
    "groq": ("https://api.groq.com/openai/v1", "whisper-large-v3"),
}


def get_transcriber(name: str = "openai"):
    """Kembalikan fungsi transkripsi (audio_path, api_key, language=None) -> Transcript."""
    if name not in ENGINES:
        raise ValueError(f"Engine transkripsi tidak dikenal: {name}")
    base_url, model = ENGINES[name]

    def _fn(audio_path: str, api_key: str, language: str | None = None) -> Transcript:
        return transcribe_openai_compatible(audio_path, api_key, language, base_url, model)

    return _fn

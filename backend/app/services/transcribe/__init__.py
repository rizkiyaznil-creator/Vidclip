"""Modul transkripsi (pluggable). Default: OpenAI Whisper API (BYOK)."""

from app.services.transcribe.base import Transcript, TranscriptWord
from app.services.transcribe.openai_whisper import transcribe_openai

__all__ = ["Transcript", "TranscriptWord", "transcribe_openai", "get_transcriber"]


def get_transcriber(name: str = "openai"):
    """Kembalikan fungsi transkripsi sesuai nama engine.

    Saat ini hanya 'openai' (BYOK). Engine lain (mis. faster-whisper lokal)
    bisa ditambahkan di sini tanpa mengubah pemanggil.
    """
    if name == "openai":
        return transcribe_openai
    raise ValueError(f"Engine transkripsi tidak dikenal: {name}")

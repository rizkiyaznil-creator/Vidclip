"""Transkripsi via OpenAI Whisper API (BYOK), dengan timestamp per kata."""

from app.services.transcribe.base import Transcript, TranscriptWord


def transcribe_openai(audio_path: str, api_key: str, language: str | None = None) -> Transcript:
    """Transkrip audio memakai Whisper (whisper-1). Auto-detect bahasa.

    `language` opsional (kode ISO mis. 'id', 'en'); biarkan None untuk deteksi
    otomatis (mendukung multi-bahasa).
    """
    from openai import OpenAI

    client = OpenAI(api_key=api_key)
    kwargs: dict = {
        "model": "whisper-1",
        "response_format": "verbose_json",
        "timestamp_granularities": ["word", "segment"],
    }
    if language:
        kwargs["language"] = language

    with open(audio_path, "rb") as f:
        resp = client.audio.transcriptions.create(file=f, **kwargs)

    words: list[TranscriptWord] = []
    for w in getattr(resp, "words", None) or []:
        # SDK mengembalikan objek; dukung juga bentuk dict.
        word = getattr(w, "word", None) if not isinstance(w, dict) else w.get("word")
        start = getattr(w, "start", None) if not isinstance(w, dict) else w.get("start")
        end = getattr(w, "end", None) if not isinstance(w, dict) else w.get("end")
        if word is not None and start is not None and end is not None:
            words.append(TranscriptWord(word=word, start=float(start), end=float(end)))

    return Transcript(
        language=getattr(resp, "language", "") or "",
        text=getattr(resp, "text", "") or "",
        words=words,
    )

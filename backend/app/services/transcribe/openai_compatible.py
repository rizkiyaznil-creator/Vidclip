"""Transkripsi via endpoint OpenAI-compatible (OpenAI, Groq, dll).

Whisper di OpenAI maupun Groq memakai API yang sama; cukup beda base_url & model.
"""

from app.services.transcribe.base import Transcript, TranscriptWord


def transcribe_openai_compatible(
    audio_path: str,
    api_key: str,
    language: str | None,
    base_url: str | None,
    model: str,
) -> Transcript:
    """Transkrip audio dgn timestamp per kata. Auto-detect bahasa bila language None."""
    from openai import OpenAI

    client = OpenAI(api_key=api_key, base_url=base_url) if base_url else OpenAI(api_key=api_key)
    kwargs: dict = {
        "model": model,
        "response_format": "verbose_json",
        "timestamp_granularities": ["word", "segment"],
    }
    if language:
        kwargs["language"] = language

    with open(audio_path, "rb") as f:
        resp = client.audio.transcriptions.create(file=f, **kwargs)

    words: list[TranscriptWord] = []
    for w in getattr(resp, "words", None) or []:
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

"""Analisis transkrip dengan Claude → daftar kandidat klip menarik (BYOK)."""

import json

from app.services.transcribe.base import Transcript

# Pemetaan pilihan user → model id sebenarnya. Default 'haiku' (hemat).
MODEL_MAP = {
    "haiku": "claude-haiku-4-5-20251001",
    "opus": "claude-opus-4-8",
}

CLIP_TOOL = {
    "name": "emit_clips",
    "description": "Kembalikan daftar segmen video paling menarik untuk dijadikan klip pendek.",
    "input_schema": {
        "type": "object",
        "properties": {
            "clips": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string", "description": "Judul singkat memikat"},
                        "start": {"type": "number", "description": "Detik mulai"},
                        "end": {"type": "number", "description": "Detik selesai"},
                        "score": {
                            "type": "integer",
                            "description": "Skor potensi viral 0-100",
                        },
                        "reason": {"type": "string", "description": "Kenapa menarik"},
                        "caption": {"type": "string", "description": "Caption siap-posting"},
                        "hashtags": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["title", "start", "end", "score"],
                },
            }
        },
        "required": ["clips"],
    },
}


def _format_transcript(transcript: Transcript, max_gap: float = 1.2) -> str:
    """Ubah kata+timestamp jadi baris ber-timestamp agar mudah dibaca model."""
    lines: list[str] = []
    cur: list[str] = []
    line_start: float | None = None
    prev_end: float | None = None

    for w in transcript.words:
        if line_start is None:
            line_start = w.start
        # Baris baru jika ada jeda besar atau kalimat berakhir.
        if cur and (
            (prev_end is not None and w.start - prev_end > max_gap)
            or cur[-1].endswith((".", "?", "!"))
            or len(cur) >= 18
        ):
            lines.append(f"[{line_start:.1f}] {' '.join(cur)}")
            cur = []
            line_start = w.start
        cur.append(w.word)
        prev_end = w.end

    if cur and line_start is not None:
        lines.append(f"[{line_start:.1f}] {' '.join(cur)}")
    return "\n".join(lines)


def _build_prompt(transcript: Transcript, instruction: str | None) -> str:
    arah = (
        f"\n\nArahan khusus dari pengguna: {instruction}\n"
        "Prioritaskan segmen yang sesuai arahan ini."
        if instruction
        else ""
    )
    return (
        "Kamu adalah editor konten video pendek yang ahli menemukan momen viral.\n"
        "Di bawah ini transkrip sebuah video dengan timestamp (dalam detik) di awal "
        "tiap baris.\n\n"
        "Tugasmu: pilih 3-10 segmen PALING MENARIK untuk dijadikan klip pendek "
        "(durasi 15-60 detik). Kriteria menarik: punya hook kuat di awal, insight/"
        "quote padat, klimaks emosi/lucu, atau cerita yang utuh.\n"
        "Aturan:\n"
        "- start/end harus jatuh di batas kalimat (jangan memotong di tengah ucapan).\n"
        "- Durasi tiap klip 15-60 detik.\n"
        "- Beri skor 0-100 sesuai potensi viral.\n"
        "- title, caption, dan hashtags mengikuti bahasa video.\n"
        f"{arah}\n\n"
        "Panggil tool emit_clips dengan hasilnya.\n\n"
        "TRANSKRIP:\n"
        f"{_format_transcript(transcript)}"
    )


def analyze_transcript(
    transcript: Transcript,
    api_key: str,
    model: str = "haiku",
    instruction: str | None = None,
) -> list[dict]:
    """Kembalikan list dict kandidat klip: title, start, end, score, reason,
    caption, hashtags. Sudah divalidasi & diklamp ke durasi transkrip."""
    from anthropic import Anthropic

    client = Anthropic(api_key=api_key)
    model_id = MODEL_MAP.get(model, MODEL_MAP["haiku"])

    resp = client.messages.create(
        model=model_id,
        max_tokens=4096,
        tools=[CLIP_TOOL],
        tool_choice={"type": "tool", "name": "emit_clips"},
        messages=[{"role": "user", "content": _build_prompt(transcript, instruction)}],
    )

    clips_raw: list[dict] = []
    for block in resp.content:
        if getattr(block, "type", None) == "tool_use" and block.name == "emit_clips":
            clips_raw = block.input.get("clips", [])
            break

    return _sanitize(clips_raw, transcript)


def _sanitize(clips_raw: list[dict], transcript: Transcript) -> list[dict]:
    total = transcript.words[-1].end if transcript.words else 0.0
    out: list[dict] = []
    for c in clips_raw:
        try:
            start = max(0.0, float(c["start"]))
            end = float(c["end"])
        except (KeyError, TypeError, ValueError):
            continue
        if total:
            end = min(end, total)
        if end - start < 3:  # buang segmen terlalu pendek/tidak valid
            continue
        out.append(
            {
                "title": str(c.get("title", "Klip"))[:300],
                "start": round(start, 2),
                "end": round(end, 2),
                "score": int(c.get("score", 0)),
                "reason": (c.get("reason") or "")[:1000],
                "caption": (c.get("caption") or "")[:2000],
                "hashtags": [str(h)[:50] for h in (c.get("hashtags") or [])][:15],
            }
        )
    out.sort(key=lambda x: x["score"], reverse=True)
    return out


# Re-export agar mudah dipakai test/JSON parsing manual.
def parse_clips_json(raw: str, transcript: Transcript) -> list[dict]:
    return _sanitize(json.loads(raw).get("clips", []), transcript)

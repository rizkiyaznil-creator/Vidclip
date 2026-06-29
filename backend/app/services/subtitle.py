"""Generate subtitle .ass gaya TikTok (word-by-word highlight) dari transkrip."""

from dataclasses import dataclass

from app.services.transcribe.base import TranscriptWord

# Resolusi target (9:16).
PLAY_W, PLAY_H = 1080, 1920


@dataclass
class Preset:
    fontname: str
    fontsize: int
    primary: str  # &HAABBGGRR
    highlight: str
    outline: str
    outline_w: int
    uppercase: bool
    max_words: int


# Beberapa preset siap pakai.
PRESETS: dict[str, Preset] = {
    "classic": Preset(
        fontname="Arial", fontsize=92, primary="&H00FFFFFF", highlight="&H0000FFFF",
        outline="&H00000000", outline_w=6, uppercase=False, max_words=4,
    ),
    "bold_caps": Preset(
        fontname="Arial", fontsize=104, primary="&H00FFFFFF", highlight="&H0000FF00",
        outline="&H00000000", outline_w=7, uppercase=True, max_words=3,
    ),
    "neon": Preset(
        fontname="Arial", fontsize=96, primary="&H00FFFFFF", highlight="&H00FF00CC",
        outline="&H00200020", outline_w=6, uppercase=False, max_words=4,
    ),
}
DEFAULT_PRESET = "classic"


def _fmt_time(t: float) -> str:
    if t < 0:
        t = 0.0
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = int(t % 60)
    cs = int(round((t - int(t)) * 100))
    if cs == 100:
        s += 1
        cs = 0
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def _group(words: list[TranscriptWord], max_words: int) -> list[list[TranscriptWord]]:
    groups: list[list[TranscriptWord]] = []
    cur: list[TranscriptWord] = []
    for w in words:
        cur.append(w)
        if len(cur) >= max_words or w.word.strip().endswith((".", "?", "!", ",")):
            groups.append(cur)
            cur = []
    if cur:
        groups.append(cur)
    return groups


def build_ass(
    words: list[TranscriptWord],
    clip_start: float,
    clip_end: float,
    preset_name: str = DEFAULT_PRESET,
) -> str:
    """Bangun isi file .ass untuk rentang [clip_start, clip_end].

    Timestamp dibuat relatif terhadap awal klip. Tiap kata aktif disorot warna.
    """
    preset = PRESETS.get(preset_name, PRESETS[DEFAULT_PRESET])

    # Ambil kata di dalam rentang & geser ke basis 0.
    sel = [
        TranscriptWord(
            word=w.word.upper() if preset.uppercase else w.word,
            start=w.start - clip_start,
            end=w.end - clip_start,
        )
        for w in words
        if w.end > clip_start and w.start < clip_end
    ]

    header = (
        "[Script Info]\n"
        "ScriptType: v4.00+\n"
        f"PlayResX: {PLAY_W}\nPlayResY: {PLAY_H}\n"
        "WrapStyle: 2\nScaledBorderAndShadow: yes\n\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
        "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, "
        "ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, "
        "MarginR, MarginV, Encoding\n"
        f"Style: Default,{preset.fontname},{preset.fontsize},{preset.primary},"
        f"&H000000FF,{preset.outline},&H64000000,1,0,0,0,100,100,0,0,1,"
        f"{preset.outline_w},2,5,60,60,40,1\n\n"
        "[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, Effect, Text\n"
    )

    lines: list[str] = []
    for group in _group(sel, preset.max_words):
        if not group:
            continue
        for i, active in enumerate(group):
            parts = []
            for j, w in enumerate(group):
                if j == i:
                    parts.append(f"{{\\c{preset.highlight}}}{w.word}{{\\c{preset.primary}}}")
                else:
                    parts.append(w.word)
            text = " ".join(parts)
            start = active.start
            # Tampilkan sampai kata berikutnya muncul (atau akhir kata ini).
            end = group[i + 1].start if i + 1 < len(group) else active.end
            if end <= start:
                end = start + 0.3
            lines.append(
                f"Dialogue: 0,{_fmt_time(start)},{_fmt_time(end)},Default,,0,0,0,,{text}"
            )

    return header + "\n".join(lines) + "\n"

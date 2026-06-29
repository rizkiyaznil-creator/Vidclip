"""Bangun filtergraph ffmpeg untuk reframe ke 9:16.

Versi M7: metode 'blur' (background blur) & 'crop' (center crop).
Face tracking (mediapipe) menyusul di M8 — antarmuka ini dibuat agar bisa
ditambah tanpa mengubah pemanggil.
"""

TARGET_W, TARGET_H = 1080, 1920


def reframe_filtergraph(method: str, subtitle_path: str | None) -> tuple[str, str]:
    """Kembalikan (filter_complex, out_label).

    out_label adalah nama pad video akhir yang harus di-`-map`.
    `subtitle_path` (bila ada) di-burn di akhir rantai.
    """
    sub = _escape_path(subtitle_path) if subtitle_path else None

    if method == "crop":
        chain = (
            f"[0:v]scale={TARGET_W}:{TARGET_H}:force_original_aspect_ratio=increase,"
            f"crop={TARGET_W}:{TARGET_H},setsar=1"
        )
        if sub:
            chain += f",subtitles='{sub}'"
        return chain + "[vout]", "[vout]"

    # default: blur background
    chain = (
        f"[0:v]split=2[bg][fg];"
        f"[bg]scale={TARGET_W}:{TARGET_H}:force_original_aspect_ratio=increase,"
        f"crop={TARGET_W}:{TARGET_H},boxblur=24:2[bgb];"
        f"[fg]scale={TARGET_W}:{TARGET_H}:force_original_aspect_ratio=decrease[fgs];"
        f"[bgb][fgs]overlay=(W-w)/2:(H-h)/2,setsar=1"
    )
    if sub:
        chain += f",subtitles='{sub}'"
    return chain + "[vout]", "[vout]"


def _escape_path(path: str) -> str:
    # Escape karakter yang bermasalah di dalam filtergraph ffmpeg.
    return path.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")

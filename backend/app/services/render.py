"""Render satu klip: potong → reframe 9:16 → burn-in subtitle."""

import os
import subprocess
import tempfile

from app.services import facetrack
from app.services.media import probe_dimensions
from app.services.reframe import reframe_filtergraph
from app.services.subtitle import build_ass
from app.services.transcribe.base import TranscriptWord


def _build_filtergraph(
    source_path: str, start: float, end: float, method: str, ass_path: str | None
) -> tuple[str, str]:
    """Pilih filtergraph reframe. 'face' memakai face tracking; bila tidak
    memungkinkan, otomatis fallback ke 'blur'."""
    if method == "face" and facetrack.is_available():
        try:
            iw, ih = probe_dimensions(source_path)
            track = facetrack.compute_track(source_path, start, end, iw, ih)
            if track:
                return facetrack.build_face_filtergraph(track, iw, ih, ass_path)
        except Exception:
            pass  # fallback di bawah
    fallback = "blur" if method == "face" else method
    return reframe_filtergraph(fallback, ass_path)


def render_clip(
    source_path: str,
    out_path: str,
    start: float,
    end: float,
    words: list[TranscriptWord],
    method: str = "blur",
    preset: str = "classic",
) -> str:
    """Hasilkan klip vertikal 9:16 dengan subtitle ter-burn di `out_path`."""
    duration = max(0.1, end - start)

    ass_path = None
    try:
        if words:
            fd, ass_path = tempfile.mkstemp(suffix=".ass")
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(build_ass(words, start, end, preset))

        filter_complex, out_label = _build_filtergraph(
            source_path, start, end, method, ass_path
        )

        cmd = [
            "ffmpeg", "-y",
            "-ss", f"{start:.3f}", "-t", f"{duration:.3f}",
            "-i", source_path,
            "-filter_complex", filter_complex,
            "-map", out_label, "-map", "0:a?",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
            "-c:a", "aac", "-b:a", "128k",
            "-movflags", "+faststart",
            out_path,
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            raise RuntimeError(f"Render gagal: {proc.stderr[-1000:]}")
        return out_path
    finally:
        if ass_path and os.path.exists(ass_path):
            os.remove(ass_path)

"""Operasi media tingkat-rendah via ffmpeg/ffprobe."""

import json
import subprocess


def _run(cmd: list[str]) -> subprocess.CompletedProcess:
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg gagal ({' '.join(cmd[:3])}…): {proc.stderr[-800:]}")
    return proc


def extract_audio(video_path: str, audio_path: str) -> str:
    """Ekstrak track audio jadi WAV mono 16kHz (optimal untuk speech-to-text)."""
    _run([
        "ffmpeg", "-y", "-i", video_path,
        "-vn", "-ac", "1", "-ar", "16000", "-f", "wav",
        audio_path,
    ])
    return audio_path


def probe_duration(path: str) -> float:
    """Durasi media dalam detik."""
    proc = _run([
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_format", path,
    ])
    return float(json.loads(proc.stdout)["format"]["duration"])


def probe_dimensions(path: str) -> tuple[int, int]:
    """Lebar & tinggi video (pixel)."""
    proc = _run([
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-select_streams", "v:0", "-show_streams", path,
    ])
    stream = json.loads(proc.stdout)["streams"][0]
    return int(stream["width"]), int(stream["height"])

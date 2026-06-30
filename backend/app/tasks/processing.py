"""Task: proses job dari upload → transkrip → analisis → kandidat klip."""

import os
import tempfile
import uuid

from app.celery_app import celery_app
from app.core import storage
from app.db import SessionLocal
from app.models import Clip, ClipStatus, Job, JobStatus, Provider
from app.services.analyze import analyze_transcript
from app.services.keys import get_decrypted_key
from app.services.media import extract_audio
from app.services.transcribe import get_transcriber
from app.services.transcribe.base import Transcript

# Engine transkripsi → provider key yang dipakai.
ENGINE_PROVIDER = {
    "openai": Provider.openai,
    "groq": Provider.groq,
}


def run_processing(job_id: str) -> None:
    """Logika inti (dipisah dari Celery agar mudah diuji/dipanggil langsung)."""
    db = SessionLocal()
    tmpdir = tempfile.mkdtemp(prefix="vidclip-")
    try:
        job = db.get(Job, uuid.UUID(job_id))
        if job is None:
            return

        # 1. Unduh sumber & ekstrak audio
        job.status = JobStatus.transcribing
        db.commit()
        ext = os.path.splitext(job.source_key or "")[1] or ".mp4"
        video_path = os.path.join(tmpdir, f"source{ext}")
        storage.download_file(job.source_key, video_path)
        audio_path = os.path.join(tmpdir, "audio.wav")
        extract_audio(video_path, audio_path)

        # 2. Transkripsi (BYOK: OpenAI atau Groq sesuai pilihan job)
        engine = job.transcribe_engine or "openai"
        provider = ENGINE_PROVIDER.get(engine, Provider.openai)
        transcribe_key = get_decrypted_key(db, job.user_id, provider)
        transcribe = get_transcriber(engine)
        transcript = transcribe(audio_path, transcribe_key, language=job.language or None)
        job.transcript = transcript.to_dict()
        job.language = job.language or transcript.language
        db.commit()

        # 3. Analisis (BYOK Claude)
        job.status = JobStatus.analyzing
        db.commit()
        anthropic_key = get_decrypted_key(db, job.user_id, Provider.anthropic)
        candidates = analyze_transcript(
            transcript, anthropic_key, model=job.model, instruction=job.instruction
        )

        # 4. Simpan kandidat klip
        for c in candidates:
            db.add(
                Clip(
                    job_id=job.id,
                    title=c["title"],
                    score=c["score"],
                    reason=c["reason"],
                    caption=c["caption"],
                    hashtags=c["hashtags"],
                    start_sec=c["start"],
                    end_sec=c["end"],
                    status=ClipStatus.candidate,
                )
            )
        job.status = JobStatus.awaiting_review
        db.commit()
    except Exception as exc:  # noqa: BLE001 - catat ke job lalu lempar ulang
        db.rollback()
        job = db.get(Job, uuid.UUID(job_id))
        if job is not None:
            job.status = JobStatus.failed
            job.error = str(exc)[:2000]
            db.commit()
        raise
    finally:
        db.close()
        _cleanup(tmpdir)


def _cleanup(path: str) -> None:
    import shutil

    shutil.rmtree(path, ignore_errors=True)


@celery_app.task(name="vidclip.process_job")
def process_job(job_id: str) -> None:
    run_processing(job_id)


# Hindari unused import (Transcript dipakai test/typing eksternal).
__all__ = ["run_processing", "process_job", "Transcript"]

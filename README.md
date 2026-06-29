# 🎬 Vidclip

Aplikasi web yang memecah video panjang menjadi klip-klip pendek yang menarik,
memotongnya otomatis, mereframe ke vertikal 9:16 (face tracking), dan menambahkan
subtitle gaya TikTok (burned-in).

> Lihat **[DESIGN.md](./DESIGN.md)** untuk arsitektur lengkap & roadmap.

## Status

🚧 Dalam pengembangan. Milestone saat ini: **M1 — Fondasi** (selesai).

| Milestone | Status |
|-----------|--------|
| M1 — Fondasi (repo, docker-compose, FastAPI, healthcheck) | ✅ |
| M2 — Auth & API key terenkripsi | ⏳ |
| M3 — Upload & object storage | ⏳ |
| M4 — Transkripsi (BYOK) | ⏳ |
| M5 — Analisis AI (kandidat klip) | ⏳ |
| M6 — Review UI | ⏳ |
| M7 — Render dasar | ⏳ |
| M8 — Face tracking + preset subtitle | ⏳ |
| M9 — Polish | ⏳ |

## Arsitektur singkat

```
Frontend (React) → Backend (FastAPI) → PostgreSQL
                        │
                        ├─ Redis (antrian) → Celery Worker (ffmpeg, face track)
                        └─ Object Storage (MinIO/S3/R2)
```

Transkripsi & analisis AI memakai **API key milik user sendiri (BYOK)**, disimpan
terenkripsi. Detail di [DESIGN.md](./DESIGN.md).

## Menjalankan (development)

Prasyarat: **Docker** & **Docker Compose**.

```bash
# 1. Siapkan environment
cp .env.example .env
# Generate master key enkripsi & tempel ke .env (MASTER_ENCRYPTION_KEY):
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# 2. Nyalakan semua service (Postgres + Redis + MinIO + backend)
docker compose up --build
```

Setelah jalan:

| Layanan | URL |
|---------|-----|
| API | http://localhost:8000 |
| Dokumentasi API (Swagger) | http://localhost:8000/docs |
| Healthcheck | http://localhost:8000/health/ready |
| MinIO Console | http://localhost:9001 (user/pass: `minioadmin`) |

Cek semua dependency siap:

```bash
curl http://localhost:8000/health/ready
# {"status":"ready","checks":{"database":"ok","redis":"ok","storage":"ok"}}
```

## Struktur proyek

```
vidclip/
├── DESIGN.md            # dokumen desain (acuan utama)
├── docker-compose.yml   # postgres + redis + minio + backend
├── .env.example
└── backend/
    └── app/
        ├── main.py      # FastAPI app
        ├── config.py    # settings dari env
        ├── db.py        # koneksi PostgreSQL
        ├── api/         # routes (health, dst.)
        └── core/        # storage, security (menyusul)
```

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
| M2 — Auth (JWT) & API key terenkripsi (BYOK) | ✅ |
| M3 — Upload & object storage | ✅ |
| M4 — Transkripsi (BYOK OpenAI Whisper) | ✅ |
| M5 — Analisis AI (kandidat klip, Claude) | ✅ |
| M6 — Frontend (upload, review, render, download) | ✅ |
| M7 — Render dasar (potong + reframe 9:16 + subtitle) | ✅ |
| M8 — Face tracking + preset subtitle tambahan | ✅ |
| M9 — Polish (kuota, batas upload, hapus job, auto-retensi) | ✅ |

**✅ Semua milestone inti (M1–M9) selesai.**

**🎉 Aplikasi sudah bisa dipakai end-to-end** (upload → klip ber-subtitle 9:16).
Reframe **mengikuti wajah pembicara** (OpenCV) dengan fallback otomatis ke blur/
center-crop. Tersedia 5 preset subtitle: `classic`, `bold_caps`, `neon`,
`minimal`, `sunny`.

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
| **Aplikasi (UI)** | **http://localhost:8000/app/** |
| API | http://localhost:8000 |
| Dokumentasi API (Swagger) | http://localhost:8000/docs |
| Healthcheck | http://localhost:8000/health/ready |
| MinIO Console | http://localhost:9001 (user/pass: `minioadmin`) |

### Cara uji end-to-end

1. Buka **http://localhost:8000/app/** → **Daftar** akun.
2. Buka panel **🔑 API Key (BYOK)** → masukkan API key untuk transkripsi
   (**OpenAI** atau **Groq** — Groq lebih hemat) dan **Anthropic/Claude**
   (untuk analisis) milikmu → Simpan.
3. **Upload Video** (boleh atur bahasa, engine transkripsi OpenAI/Groq, model
   analisis, & arahan seperti "cari momen lucu") → klik **Proses Video**.
4. Tunggu status berubah jadi **Siap direview** → muncul daftar kandidat klip
   dengan skor.
5. Centang klip yang diinginkan, pilih preset subtitle → **Render klip terpilih**.
6. Setelah **Selesai**, klik **Download** untuk ambil klip 9:16 ber-subtitle.

> UI memakai Tailwind via CDN (butuh internet untuk styling; fungsionalitas tetap
> jalan tanpa styling). Migrasi ke React ada di roadmap.

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

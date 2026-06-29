# Vidclip — Dokumen Desain

> Aplikasi web yang memecah video panjang menjadi klip-klip pendek yang menarik,
> memotongnya secara otomatis, mereframe ke format vertikal, dan menambahkan
> subtitle gaya TikTok (burned-in).

Dokumen ini adalah **single source of truth** untuk arsitektur & keputusan
produk Vidclip. Diperbarui seiring perkembangan proyek.

---

## 1. Ringkasan Produk

Pengguna mengunggah video panjang (podcast, webinar, vlog, stream). Vidclip:

1. Mentranskripsi audio (speech-to-text, multi-bahasa, auto-detect).
2. Menganalisis transkrip dengan AI untuk menemukan momen paling menarik.
3. Menampilkan **kandidat klip** (judul, skor, alasan, waktu) untuk di-_review_ pengguna.
4. Merender klip terpilih: potong → reframe ke 9:16 (face tracking) → burn-in subtitle.
5. Pengguna mengunduh klip siap-posting.

**Target pengguna:** multi-user (ada login, isolasi data per user).

---

## 2. Keputusan Desain Inti

| Aspek | Keputusan | Catatan |
|-------|-----------|---------|
| Bentuk aplikasi | Web app, multi-user | Ada autentikasi/login |
| Bahasa video | Multi-bahasa (auto-detect) | |
| Transkripsi | **BYOK** — OpenAI Whisper API (key user) | Modul _pluggable_; opsi faster-whisper lokal tersedia |
| Analisis "menarik" | **BYOK** — Claude API (key user) | |
| Model AI default | **Claude Haiku** (hemat) | Opus sebagai pilihan kedua (kualitas) |
| Instruksi kustom | Ya — user bisa arahkan (mis. "cari momen lucu") | Diteruskan ke prompt analisis |
| Penyimpanan API key | **Terenkripsi at-rest** (Fernet) | Tak pernah plaintext / masuk log / dikirim utuh ke client |
| Alur pemilihan | **Review dulu → baru render** | Hemat waktu & resource |
| Output | Vertikal **9:16** | |
| Reframe | **Face tracking (mediapipe)** | Fallback ke blur/crop bila server kewalahan |
| Subtitle | **Burned-in, gaya TikTok**, beberapa preset | Format `.ass` (word-by-word highlight) |
| Database | **PostgreSQL** | |
| Storage | **Object storage** (dev: MinIO, prod: S3/R2) | |
| Antrian | **Celery + Redis** | |

---

## 3. Arsitektur

```
┌─────────────┐     ┌──────────────────────┐     ┌──────────────┐
│  Frontend   │────▶│   Backend (FastAPI)  │────▶│  PostgreSQL  │
│  (React)    │     │  - Auth/login (JWT)  │     │  users, jobs,│
└─────────────┘     │  - Kelola job        │     │  clips, keys │
                    │  - Dekripsi key user │     └──────────────┘
                    └──────────┬───────────┘
                               │ enqueue
                          ┌────▼─────┐
                          │  Redis   │  (broker antrian)
                          └────┬─────┘
                               │ consume
                    ┌──────────▼───────────┐     ┌──────────────┐
                    │   Celery Worker(s)   │────▶│Object Storage│
                    │  - Transkrip (OpenAI)│     │ video & klip │
                    │  - Analisis (Claude) │     │ (MinIO/S3/R2)│
                    │  - ffmpeg cut+render │     └──────────────┘
                    │  - Face track (mp)   │
                    └──────────────────────┘
```

**Beban server:** karena transkripsi & analisis BYOK (pindah ke API user), kerja
berat di server tinggal **ffmpeg render + face tracking**. Face tracking adalah
komponen paling rakus CPU yang tersisa → perlu diuji & diberi fallback otomatis.

---

## 4. Pipeline Pemrosesan

```
1. Upload video                → simpan ke object storage, buat record `job`
2. Ekstrak audio (ffmpeg)      → audio.wav sementara
3. Transkripsi (BYOK OpenAI)   → teks + timestamp per kata (JSON)
4. Analisis AI (BYOK Claude)   → daftar kandidat klip (JSON terstruktur):
                                  { start, end, judul, skor(0-100), alasan,
                                    hashtag[], caption }
   ── status: AWAITING_REVIEW ──
5. [PENGGUNA REVIEW & pilih klip]
6. Render tiap klip terpilih:
     a. Cut segmen (ffmpeg)
     b. Reframe 9:16 (mediapipe face tracking + smoothing; fallback blur/crop)
     c. Burn-in subtitle (.ass, preset terpilih)
7. Simpan klip ke storage      → status: DONE
8. Pengguna unduh
```

**Aturan segmen AI:** durasi 15–60 dtk, mulai/berhenti di batas kalimat (tidak
memotong di tengah omongan).

---

## 5. Skema Database (ringkas)

```
users
  id            uuid pk
  email         text unique
  password_hash text
  created_at    timestamptz

api_keys
  id            uuid pk
  user_id       uuid fk -> users
  provider      enum('openai','anthropic')
  ciphertext    bytea          -- key terenkripsi (Fernet)
  hint          text           -- mis. "sk-...abc3" untuk ditampilkan
  created_at    timestamptz

jobs
  id            uuid pk
  user_id       uuid fk -> users
  status        enum('uploaded','transcribing','analyzing',
                     'awaiting_review','rendering','done','failed')
  source_key    text           -- path video di object storage
  language      text
  instruction   text           -- arahan kustom user (boleh null)
  ai_model      text           -- mis. 'claude-haiku', 'claude-opus'
  error         text
  created_at    timestamptz

clips
  id            uuid pk
  job_id        uuid fk -> jobs
  title         text
  score         int
  reason        text
  caption       text
  hashtags      text[]
  start_sec     float
  end_sec       float
  selected      bool           -- dipilih user untuk dirender
  output_key    text           -- path klip hasil (null bila belum render)
  subtitle_preset text
  status        enum('candidate','rendering','done','failed')
```

---

## 6. Keamanan

- **API key user** dienkripsi dengan **Fernet** memakai `MASTER_ENCRYPTION_KEY`
  (env var, tidak di kode/VCS). Didekripsi hanya di memori worker saat dipakai.
- Key **tak pernah** disimpan plaintext, masuk log, atau dikirim utuh ke client
  (hanya `hint` yang ditampilkan).
- Password di-hash (bcrypt/argon2). Auth via JWT.
- Kuota per user & rate-limit untuk cegah abuse.
- Validasi tipe & ukuran file upload.

---

## 7. Struktur Folder (rencana)

```
vidclip/
├── DESIGN.md
├── docker-compose.yml         # postgres + redis + minio (+ backend) untuk dev
├── .env.example
├── backend/
│   ├── pyproject.toml
│   ├── app/
│   │   ├── main.py            # FastAPI app
│   │   ├── config.py          # settings (pydantic-settings)
│   │   ├── db.py              # SQLAlchemy engine/session
│   │   ├── models/            # ORM models
│   │   ├── schemas/           # Pydantic schemas
│   │   ├── api/               # routes: auth, keys, jobs, clips
│   │   ├── core/
│   │   │   ├── security.py    # JWT, hashing, Fernet enkripsi key
│   │   │   └── storage.py     # abstraksi object storage (S3/MinIO)
│   │   ├── services/
│   │   │   ├── transcribe/    # pluggable: openai / faster-whisper
│   │   │   ├── analyze.py     # Claude → kandidat klip
│   │   │   ├── reframe.py     # mediapipe face tracking + fallback
│   │   │   ├── subtitle.py    # generate .ass + preset
│   │   │   └── render.py      # ffmpeg orchestration
│   │   └── tasks/             # Celery tasks
│   └── alembic/               # migrasi DB
└── frontend/
    ├── package.json
    └── src/                   # React + Vite + Tailwind
        ├── pages/             # login, dashboard, upload, review, hasil
        └── components/
```

---

## 8. Roadmap Milestone

Tiap milestone bisa diuji & di-commit terpisah.

| # | Milestone | Isi |
|---|-----------|-----|
| **M1** | Fondasi | Struktur repo, docker-compose (pg/redis/minio), FastAPI jalan, config, healthcheck |
| **M2** | Auth & key | Register/login (JWT), CRUD API key terenkripsi |
| **M3** | Upload & storage | Upload video → object storage, record job, ekstrak audio |
| **M4** | Transkripsi | Modul pluggable (OpenAI BYOK) → transkrip+timestamp |
| **M5** | Analisis AI | Claude → kandidat klip JSON (+ instruksi kustom, pilih model) |
| **M6** | Review UI | Frontend: lihat kandidat, pilih klip |
| **M7** | Render dasar | Cut + reframe (blur/crop) + subtitle 1 preset |
| **M8** | Face tracking + preset | mediapipe + multi preset subtitle |
| **M9** | Polish | Progress real-time, error handling, kuota, packaging |

---

## 9. Catatan / Risiko Terbuka

- **Face tracking di CPU** bisa lambat untuk video panjang → perlu benchmark &
  fallback otomatis (M8).
- **Biaya storage** tumbuh dengan jumlah user → kebijakan retensi (auto-hapus
  setelah N hari) + kuota.
- **Environment dev efemeral** → jangan andalkan disk lokal sebagai penyimpanan
  permanen; object storage sejak awal.
- **Rate limit API user** (OpenAI/Anthropic) → tangani error & retry yang rapi.

"""Reframe 9:16 dengan mengikuti wajah pembicara (OpenCV Haar cascade).

Strategi: sampel beberapa frame per detik, deteksi wajah terbesar, haluskan
lintasan posisi, lalu bangun ekspresi crop ffmpeg yang "meman" mengikuti wajah
dalam SATU pass (sehingga subtitle + audio + encode tetap satu perintah).

Detektor memakai Haar cascade bawaan OpenCV (tanpa unduh model, jalan offline).
Bila OpenCV tak ada, sumber bukan landscape, atau wajah tak terdeteksi, fungsi
mengembalikan None → pemanggil fallback ke blur/crop.
"""

import os

TARGET_W, TARGET_H = 1080, 1920
TARGET_RATIO = TARGET_W / TARGET_H  # 0.5625 (9:16)


def _cascade_path() -> str | None:
    try:
        import cv2

        path = os.path.join(cv2.data.haarcascades, "haarcascade_frontalface_default.xml")
        return path if os.path.exists(path) else None
    except Exception:
        return None


def is_available() -> bool:
    return _cascade_path() is not None


def compute_track(
    video_path: str,
    start: float,
    end: float,
    iw: int,
    ih: int,
    sample_fps: float = 3.0,
) -> list[tuple[float, float]] | None:
    """Kembalikan list (t_relatif, x_center_px) hasil deteksi+penghalusan,
    atau None bila tak layak (fallback)."""
    # Hanya untuk sumber yang lebih lebar dari 9:16 (perlu memilih irisan vertikal).
    if iw <= 0 or ih <= 0 or (iw / ih) <= TARGET_RATIO + 1e-3:
        return None

    cascade_path = _cascade_path()
    if cascade_path is None:
        return None

    import cv2

    detector = cv2.CascadeClassifier(cascade_path)
    if detector.empty():
        return None

    # Downscale untuk kecepatan deteksi; koordinat dikembalikan ke skala asli.
    scale = 640.0 / iw if iw > 640 else 1.0
    cap = cv2.VideoCapture(video_path)
    try:
        raw: list[tuple[float, float | None]] = []
        t = start
        step = 1.0 / sample_fps
        while t < end:
            cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000.0)
            ok, frame = cap.read()
            if not ok:
                break
            small = cv2.resize(frame, None, fx=scale, fy=scale) if scale != 1.0 else frame
            gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
            faces = detector.detectMultiScale(
                gray, scaleFactor=1.1, minNeighbors=5,
                minSize=(int(small.shape[0] * 0.08), int(small.shape[0] * 0.08)),
            )
            cx: float | None = None
            if len(faces) > 0:
                # Wajah dengan area terbesar (heuristik: pembicara dominan/terdekat).
                x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
                cx = (x + w / 2) / scale
            raw.append((t - start, cx))
            t += step
    finally:
        cap.release()

    detected = [c for _, c in raw if c is not None]
    # Butuh deteksi yang cukup agar tracking bermakna; jika sedikit → fallback.
    if not raw or len(detected) < max(2, len(raw) * 0.3):
        return None

    # Isi nilai kosong dengan menahan nilai terakhir.
    first = detected[0]
    filled: list[tuple[float, float]] = []
    last = first
    for ti, c in raw:
        last = c if c is not None else last
        filled.append((ti, last))

    smoothed = _smooth([c for _, c in filled], window=5)
    half = ih * TARGET_RATIO / 2
    clamped = [min(max(c, half), iw - half) for c in smoothed]
    return _decimate(
        [(filled[i][0], clamped[i]) for i in range(len(filled))],
        min_delta=iw * 0.012,
        max_gap=2.0,
    )


def _smooth(values: list[float], window: int) -> list[float]:
    n = len(values)
    out = []
    half = window // 2
    for i in range(n):
        lo, hi = max(0, i - half), min(n, i + half + 1)
        out.append(sum(values[lo:hi]) / (hi - lo))
    return out


def _decimate(
    points: list[tuple[float, float]], min_delta: float, max_gap: float
) -> list[tuple[float, float]]:
    """Buang keyframe yang nyaris tak berubah agar ekspresi ffmpeg ringkas."""
    if not points:
        return points
    kept = [points[0]]
    for t, x in points[1:]:
        lt, lx = kept[-1]
        if abs(x - lx) >= min_delta or (t - lt) >= max_gap:
            kept.append((t, x))
    if kept[-1] != points[-1]:
        kept.append(points[-1])
    return kept


def build_face_filtergraph(
    track: list[tuple[float, float]], iw: int, ih: int, subtitle_path: str | None
) -> tuple[str, str]:
    """Bangun filter_complex crop bergerak (mengikuti wajah) → skala 9:16."""
    from app.services.reframe import _escape_path

    cw = min(int(round(ih * TARGET_RATIO)), iw)
    x_expr = _xcenter_expr(track)  # ekspresi pusat-x (px) terhadap waktu t
    # x kiri crop = clip(center - cw/2, 0, iw-cw); koma di-escape utk filtergraph.
    left = f"min(max(({x_expr})-{cw / 2:.1f}\\,0)\\,{iw - cw})"
    chain = (
        f"[0:v]crop={cw}:{ih}:x='{left}':y=0,"
        f"scale={TARGET_W}:{TARGET_H},setsar=1"
    )
    if subtitle_path:
        chain += f",subtitles='{_escape_path(subtitle_path)}'"
    return chain + "[vout]", "[vout]"


def _xcenter_expr(track: list[tuple[float, float]]) -> str:
    """Ekspresi piecewise-linear pusat-x(px) terhadap t (detik, basis 0)."""
    if len(track) == 1:
        return f"{track[0][1]:.1f}"

    expr = f"{track[-1][1]:.1f}"  # setelah keyframe terakhir → tahan
    for i in range(len(track) - 2, -1, -1):
        t0, x0 = track[i]
        t1, x1 = track[i + 1]
        dt = max(t1 - t0, 1e-3)
        seg = f"({x0:.1f}+({x1 - x0:.1f})*(t-{t0:.3f})/{dt:.3f})"
        expr = f"if(lt(t\\,{t1:.3f})\\,{seg}\\,{expr})"
    t_first, x_first = track[0]
    expr = f"if(lt(t\\,{t_first:.3f})\\,{x_first:.1f}\\,{expr})"
    return expr

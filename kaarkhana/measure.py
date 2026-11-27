"""Video pass -> per-station time series (the 'event stream' source)."""
from __future__ import annotations
from dataclasses import dataclass
import cv2
import numpy as np
from .calibrate import Geometry


@dataclass
class Signals:
    t: np.ndarray            # (T,) seconds (video time)
    work_area: np.ndarray    # (T,N) fraction of work-spot ROI covered by fabric
    work_lab: np.ndarray     # (T,N,3) mean Lab colour of that fabric (nan if none)
    queue_area: np.ndarray   # (T,N) fabric pixels in queue ROI, normalised by pitch^2
    fps: float
    duration: float


def _lab_mean(band_lab, mask):
    if mask.sum() < 20:
        return np.full(3, np.nan)
    return band_lab[mask].mean(0)


def extract(video_path, geom: Geometry, detector, sample_hz=10.0, fit_frames=80,
            progress=None, max_seconds=None) -> Signals:
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"cannot open {video_path}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    nframes = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    ok, first = cap.read()
    if not ok or first is None:
        cap.release()
        raise RuntimeError(f"cannot read the first frame of {video_path}")
    x0, y0, x1, y1 = geom.band(first.shape)
    rois = geom.rois((x0, y0))
    N = geom.n
    dur = nframes / fps
    if max_seconds:
        dur = min(dur, max_seconds)

    def prep(fr):
        return fr[y0:y1, x0:x1]

    # 1) learn static scene (classical) from frames spread across the clip
    fits = []
    for k in np.linspace(0, max(nframes - 2, 1), fit_frames).astype(int):
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(k))
        ok, fr = cap.read()
        if ok and fr is not None:
            fits.append(prep(fr))
    if fits:
        detector.fit(fits)

    # 2) sample the clip
    step = max(int(round(fps / sample_hz)), 1)
    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
    T = int(dur * fps // step) + 1
    wa = np.zeros((T, N)); wl = np.full((T, N, 3), np.nan); qa = np.zeros((T, N)); ts = np.zeros(T)
    p2 = geom.pitch_px ** 2
    i = idx = 0
    while True:
        ok = cap.grab()
        if not ok or idx >= T:
            break
        if i % step == 0:
            ok, fr = cap.retrieve()
            if not ok or fr is None:
                break
            band = prep(fr)
            m = detector.fabric_mask(band)
            lab = cv2.cvtColor(band, cv2.COLOR_BGR2LAB).astype(np.float32)
            for s, (w, q) in enumerate(rois):
                wm = m[w[1]:w[3], w[0]:w[2]]
                wa[idx, s] = wm.mean() if wm.size else 0
                wl[idx, s] = _lab_mean(lab[w[1]:w[3], w[0]:w[2]], wm)
                qm = m[q[1]:q[3], q[0]:q[2]]
                qa[idx, s] = qm.sum() / p2
            ts[idx] = i / fps
            idx += 1
            if progress and idx % 50 == 0:
                progress(min(i / fps / dur, 1.0))
        i += 1
    cap.release()
    return Signals(ts[:idx], wa[:idx], wl[:idx], qa[:idx], fps, float(ts[idx - 1]) if idx else 0.0)

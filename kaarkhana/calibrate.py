"""Camera calibration: where are the stations, and how big is a metre?

Everything downstream works in units of *station pitch* (distance between
adjacent stations, known from the layout), so it is independent of resolution
and of camera distance. For oblique cameras, supply a 4-point homography and
the frames are rectified onto the table plane first.
"""
from __future__ import annotations
from dataclasses import dataclass
import cv2
import numpy as np


@dataclass
class Geometry:
    anchors: np.ndarray                  # (N,2) pixel centre of each station marker
    pitch_px: float                      # mean pixel distance between stations
    px_per_m: float
    homography: np.ndarray | None = None  # optional rectification (3x3), applied to frames

    @property
    def n(self):
        return len(self.anchors)

    def band(self, frame_shape):
        """Pixel box (x0,y0,x1,y1) of the strip that contains the line."""
        h, w = frame_shape[:2]
        p = self.pitch_px
        x0 = int(max(0, self.anchors[:, 0].min() - 0.9 * p))
        x1 = int(min(w, self.anchors[:, 0].max() + 0.9 * p))
        y0 = int(max(0, self.anchors[:, 1].mean() - 0.25 * p))
        y1 = int(min(h, self.anchors[:, 1].mean() + 1.15 * p))
        return x0, y0, x1, y1

    def rois(self, band_xy):
        """Work-spot and queue ROIs per station, in band coordinates.

        Defined as fractions of the station pitch, measured on the reference
        layout: the machine needle sits at the station marker; the incoming
        queue lies on the table just upstream (to the left, flow is L->R).
        """
        x0, y0 = band_xy
        p = self.pitch_px
        out = []
        for ax, ay in self.anchors:
            cx, cy = ax - x0, ay - y0
            work = (int(cx - 0.20 * p), int(cy + 0.40 * p), int(cx + 0.12 * p), int(cy + 0.70 * p))
            queue = (int(cx - 0.66 * p), int(cy + 0.15 * p), int(cx - 0.22 * p), int(cy + 0.88 * p))
            out.append((work, queue))
        return out


def from_two_points(p_first, p_last, n, pitch_m, homography=None) -> Geometry:
    """Tap the first and last station marker -> interpolate the rest."""
    a = np.linspace(np.asarray(p_first, float), np.asarray(p_last, float), n)
    pitch = float(np.linalg.norm(a[1] - a[0]))
    return Geometry(a, pitch, pitch / pitch_m, homography)


def auto_find_signs(frame_bgr, n) -> Geometry | None:
    """Locate station name-plates (saturated blue/red tags) automatically.

    Works on lines whose stations carry coloured plates (as in the reference
    sim and in most factories that tag stations). Returns None if exactly n
    plates are not found - then use from_two_points().
    """
    h, w = frame_bgr.shape[:2]
    b, g, r = [frame_bgr[..., i].astype(np.int16) for i in range(3)]
    mask = (((b > 110) & (r < 60) & (g < 90)) | ((r > 150) & (g < 60) & (b < 60))).astype(np.uint8) * 255
    k = np.ones((max(3, w // 384), max(5, w // 128)), np.uint8)       # scale with resolution
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, k)
    cnt, _, stats, cen = cv2.connectedComponentsWithStats(mask)
    # plates: wide, short blobs of similar size, in one horizontal row
    cand = [(cen[i], stats[i]) for i in range(1, cnt)
            if stats[i][4] > 0.00002 * w * h and 2.0 < stats[i][2] / max(stats[i][3], 1) < 6]
    if len(cand) < n:
        return None
    best = None
    for yc in {round(c[0][1] / 10) * 10 for c in cand}:
        row = [c for c in cand if abs(c[0][1] - yc) < max(8, h * 0.015)]
        if len(row) >= n:
            areas = np.array([c[1][4] for c in row]); med = np.median(areas)
            row = [c for c in row if 0.5 * med < c[1][4] < 1.6 * med]
            if len(row) == n:
                best = row
                break
    if best is None:
        return None
    pts = np.array(sorted([c[0] for c in best], key=lambda c: c[0]))
    return Geometry(pts, float(np.mean(np.diff(pts[:, 0]))), 0.0)


def finalize(geom: Geometry, pitch_m: float) -> Geometry:
    geom.px_per_m = geom.pitch_px / pitch_m
    return geom


# work-spot ROI area in units of pitch^2 (0.32 p wide x 0.30 p tall) - used to
# convert fabric coverage into "bundle-equivalents"
WORK_ROI_P2 = 0.32 * 0.30

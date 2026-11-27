"""Signals -> bundle 'visit' events (arrive, work, depart) per station.

A visit is one bundle sitting in a station's work spot. Consecutive bundles
are separated either by an empty gap, or - when back-to-back with no gap -
by a change in fabric colour (each bundle has its own appearance).
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from .measure import Signals


def _runs(mask):
    """(start, end) index pairs (end exclusive) of True runs."""
    d = np.diff(np.r_[0, mask.astype(np.int8), 0])
    return list(zip(np.where(d == 1)[0], np.where(d == -1)[0]))


def _presence(area, on=0.10, off=0.05, close_gap=1):
    p = np.zeros(len(area), bool)
    state = False
    for i, a in enumerate(area):
        state = (a > off) if state else (a > on)
        p[i] = state
    # bridge short dropouts (hands passing over the bundle)
    for s, e in _runs(~p):
        if s > 0 and e < len(p) and (e - s) <= close_gap:
            p[s:e] = True
    return p


def _split_by_colour(lab, s, e, de=14.0, persist=3, min_len=6):
    """Split a present-run where the fabric colour jumps and stays changed."""
    cuts = [s]
    ref_start = s
    i = s + 2
    while i < e - persist:
        ref = np.nanmedian(lab[ref_start:i], axis=0) if i - ref_start >= 2 else lab[ref_start]
        cur = lab[i:i + persist]
        if np.all(np.isfinite(cur)) and np.all(np.linalg.norm(cur - ref, axis=1) > de) \
                and (i - ref_start) >= min_len:
            cuts.append(i)
            ref_start = i
            i += min_len
        else:
            i += 1
    cuts.append(e)
    return list(zip(cuts[:-1], cuts[1:]))


def build_events(sig: Signals, station_ids, min_visit_s=1.5, de=14.0) -> pd.DataFrame:
    dt = float(np.median(np.diff(sig.t)))
    rows = []
    for s, sid in enumerate(station_ids):
        pres = _presence(sig.work_area[:, s])
        for a, b in _runs(pres):
            for u, v in _split_by_colour(sig.work_lab[:, s, :], a, b, de=de):
                dur = (v - u) * dt
                if dur < min_visit_s:
                    continue
                rows.append(dict(station=sid, idx=s, t_start=sig.t[u], t_end=sig.t[min(v, len(sig.t) - 1)],
                                 duration=dur,
                                 censored=bool(u == 0 or v >= len(sig.t))))
    return pd.DataFrame(rows).sort_values(["idx", "t_start"]).reset_index(drop=True)

"""Score the pipeline against a simulated line with KNOWN cycle times.

Honest scope: this validates measurement + constraint logic on a simulation.
It is not a claim about accuracy on a live factory floor.
"""
from __future__ import annotations
import json
import numpy as np
from scipy.stats import pearsonr, spearmanr


def score(res, truth_path) -> dict:
    with open(truth_path, encoding="utf-8") as fh:
        gt = json.load(fh)
    g = np.array(gt["sim_cycle_sec"], float) * 1.025          # mean of the x(0.8..1.25) jitter
    o = res["table"].cycle_med_s.values.astype(float)
    ok = ~np.isnan(o)
    scale = np.nanmedian(o[ok] / g[ok])                       # global clock/hand-off offset
    err = np.abs(o[ok] / scale - g[ok]) / g[ok]
    gi = int(np.argmax(g))
    others = np.delete(np.arange(len(g)), gi)
    return dict(
        constraint_correct=res["constraint"].id == gt["bottleneck"],
        found=res["constraint"].id, truth=gt["bottleneck"], confidence=res["constraint"].confidence,
        pearson_r=float(pearsonr(o[ok], g[ok])[0]), spearman=float(spearmanr(o[ok], g[ok])[0]),
        ratio_measured=float(o[gi] / np.nanmedian(o[others])),
        ratio_truth=float(g[gi] / np.median(g[others])),
        global_offset=float(scale),
        mape_after_global_offset=float(err.mean()), worst_station_err=float(err.max()),
        n_visits=int(res["table"].visits.sum()), span_s=res["span_s"],
        recommended=res["recommended"]["scn"].name,
        note="Absolute times read ~1.1-1.3x high (hand-off included in a visit); relative structure is what is validated.")

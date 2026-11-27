"""Station metrics, constraint identification, SMV reconciliation."""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np
import pandas as pd
from .calibrate import WORK_ROI_P2
from .config import LineConfig
from .measure import Signals


def station_table(ev: pd.DataFrame, sig: Signals, cfg: LineConfig) -> pd.DataFrame:
    span = sig.duration
    wa = sig.work_area
    on = wa[wa > 0.10]
    unit = (np.median(on) if on.size else 0.2) * WORK_ROI_P2          # one bundle, in pitch^2
    rows = []
    for i, st in enumerate(cfg.stations):
        e = ev[(ev.idx == i)]
        full = e[~e.censored]
        cyc = full.duration.values
        busy = e.duration.sum()
        q = sig.queue_area[:, i] / unit
        t_min = sig.t / 60.0
        slope = float(np.polyfit(t_min, q, 1)[0]) if len(q) > 3 else 0.0
        rows.append(dict(
            id=st.id, name=st.name, operators=st.operators, visits=len(full),
            cycle_med_s=float(np.median(cyc)) if len(cyc) else np.nan,
            cycle_mean_s=float(np.mean(cyc)) if len(cyc) else np.nan,
            cycle_p90_s=float(np.percentile(cyc, 90)) if len(cyc) else np.nan,
            busy_frac=float(min(busy / span, 1.0)) if span else 0.0,
            queue_mean=float(np.mean(q)), queue_p90=float(np.percentile(q, 90)),
            queue_trend_per_min=slope,
        ))
    df = pd.DataFrame(rows)
    df["cycle_per_op_s"] = df.cycle_med_s / df.operators
    return df


@dataclass
class Constraint:
    idx: int
    id: str
    name: str
    confidence: str
    margin: float                       # slowest / next-slowest (per operator)
    evidence: list                      # [(label, bool, detail)]


def find_constraint(tab: pd.DataFrame) -> Constraint:
    c = np.asarray(tab.cycle_per_op_s.values, float)
    valid = np.flatnonzero(np.isfinite(c))
    if valid.size < 2:
        raise RuntimeError(
            "Need cycle times for at least two stations to name a constraint; "
            "check calibration, the detector and the length of the clip.")
    # Slowest and next-slowest per-operator cycle; ignore stations with no visits.
    i = int(valid[np.argmax(c[valid])])
    j = int(max((k for k in valid if k != i), key=lambda k: c[k]))
    others = c[[k for k in valid if k != i]]
    median = float(np.median(others))
    margin = float(c[i] / c[j]) if c[j] > 0 else float("inf")
    vs_med = float(c[i] / median) if median > 0 else float("inf")

    ev = [("Longest cycle per operator", True,
           f"{c[i]:.1f}s vs {median:.1f}s median of the rest ({vs_med:.1f}x), next slowest {tab.id[j]} {c[j]:.1f}s")]

    # starvation edge: busy fraction falls sharply right after the constraint
    b = tab.busy_frac.values
    drops = [(b[k] - b[k + 1]) / b[k] if b[k] > 0.05 else 0 for k in range(len(b) - 1)]
    k = int(np.argmax(drops)) if drops else 0
    edge_ok = k == i and drops[k] > 0.3
    ev.append(("Downstream starvation right after it", edge_ok,
               f"busy {b[k]*100:.0f}% -> {b[k+1]*100:.0f}% across {tab.id[k]}->{tab.id[k+1]}" if drops else "n/a"))

    # work piling in front (exclude station 1: its 'queue' is the raw cutting-table stock)
    qp = tab.queue_p90.values.copy(); qp[0] = -1
    qi = int(np.argmax(qp))
    ev.append(("Largest WIP queue in front (excl. cut stock)", qi == i,
               f"{tab.id[qi]} peak {qp[qi]:.1f} bundle-equiv; {tab.id[i]} peak {tab.queue_p90[i]:.1f}"))

    agree = sum(1 for _, ok, _ in ev if ok)
    if margin >= 1.3 and agree >= 2:
        conf = "high"
    elif margin >= 1.15 or agree >= 2:
        conf = "medium"
    else:
        conf = "low"
    return Constraint(i, tab.id[i], tab.name[i], conf, vs_med, ev)


def reconcile(tab: pd.DataFrame, cfg: LineConfig, tol=0.25) -> pd.DataFrame:
    """Observed vs the factory's own SMV sheet.

    pace = observed real time / basic SMV time. The *line median* pace is what
    the operators actually run at; a station whose pace deviates from it by more
    than `tol` disagrees with the sheet (stale SMV, method change, or a real
    problem) and is flagged for the IE to look at.
    """
    r = tab[["id", "name"]].copy()
    r["observed_s"] = tab.cycle_med_s.values * cfg.time_scale
    r["sheet_basic_s"] = [(s.basic_smv_min or np.nan) * 60 for s in cfg.stations]
    r["sheet_std_s"] = [(s.std_smv_min or np.nan) * 60 for s in cfg.stations]
    r["pace"] = r.observed_s / r.sheet_basic_s
    line_pace = float(np.nanmedian(r.pace))
    r["dev_vs_line_pace"] = r.pace / line_pace - 1
    r["flag"] = r.dev_vs_line_pace.abs() > tol
    r.attrs["line_pace"] = line_pace
    return r

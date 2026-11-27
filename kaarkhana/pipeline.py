"""Orchestrator: video -> measurements -> constraint -> prescription -> report."""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import cv2
from . import analysis as A, balance as B, calibrate as C, detect as D, measure as M
from .config import LineConfig
from .events import build_events
from .agent import RuleAgent


def _clean(o):
    if isinstance(o, dict):
        return {k: _clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_clean(v) for v in o]
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return None if np.isnan(o) else float(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, float) and np.isnan(o):
        return None
    return o


def calibrate_video(video, cfg: LineConfig, anchors=None, probe_s=150):
    cap = cv2.VideoCapture(str(video))
    nfr, fps = cap.get(cv2.CAP_PROP_FRAME_COUNT), cap.get(cv2.CAP_PROP_FPS) or 30
    cap.set(cv2.CAP_PROP_POS_FRAMES, int(min(probe_s * fps, max(nfr - 2, 0))))
    ok, fr = cap.read()
    cap.release()
    if not ok:
        raise RuntimeError("cannot read video")
    if anchors:
        g = C.from_two_points(anchors[0], anchors[1], cfg.n, cfg.pitch_m)
    else:
        g = C.auto_find_signs(fr, cfg.n)
        if g is None:
            raise RuntimeError("Could not auto-locate the station plates. Pass anchors=((x,y),(x,y)): "
                               "pixel centre of the first and last station.")
        g = C.finalize(g, cfg.pitch_m)
    return g, fr


def analyse(video, cfg: LineConfig, detector=None, anchors=None, sample_hz=10.0,
            progress=None, max_seconds=None, feed_rate_hr=None, agent=None):
    detector = detector or D.ClassicalDetector()
    geom, probe = calibrate_video(video, cfg, anchors)
    sig = M.extract(video, geom, detector, sample_hz=sample_hz, progress=progress, max_seconds=max_seconds)
    ids = [s.id for s in cfg.stations]
    ev = build_events(sig, ids)
    tab = A.station_table(ev, sig, cfg)
    con = A.find_constraint(tab)
    rec = A.reconcile(tab, cfg)

    work_min = (tab.cycle_med_s.fillna(tab.cycle_med_s.median()).values * cfg.time_scale / 60).tolist()
    ops0 = [s.operators for s in cfg.stations]
    scn = B.scenarios(work_min, ops0, ids)
    costs = [B.cost(s, scn[0], feed_rate_hr, cfg.costing) for s in scn]
    # recommendation: best net value among same-headcount and +1 operator
    cand = [k for k, s in enumerate(scn) if s.kind in ("shift", "add") and s.extra_operators <= 1]
    best = max(cand, key=lambda k: costs[k]["net_day_bdt"])
    # same-line view on the factory's own SMV (sheet basis)
    smv_work = [(s.std_smv_min or np.nan) for s in cfg.stations]
    smv_scn = B.scenarios(smv_work, ops0, ids) if not np.isnan(smv_work).any() else None

    res = dict(cfg=cfg, geom=geom, signals=sig, events=ev, table=tab, constraint=con, recon=rec,
               scenarios=scn, costs=costs, recommended=dict(scn=scn[best], cost=costs[best], idx=best),
               smv_scenarios=smv_scn, span_s=sig.duration, detector=detector.name, probe_frame=probe)
    res["story"] = (agent or RuleAgent()).write(res)
    return res


def save_outputs(res, out_dir) -> dict:
    from .report import make_report
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    res["table"].to_csv(out / "station_metrics.csv", index=False)
    res["events"].to_csv(out / "bundle_events.csv", index=False)
    res["recon"].to_csv(out / "smv_reconciliation.csv", index=False)
    summary = dict(
        line=res["cfg"].name, detector=res["detector"], span_s=res["span_s"],
        constraint=dict(id=res["constraint"].id, name=res["constraint"].name,
                        confidence=res["constraint"].confidence, ratio_vs_rest=res["constraint"].margin,
                        evidence=[dict(label=a, ok=bool(b), detail=c) for a, b, c in res["constraint"].evidence]),
        stations=res["table"].to_dict("records"),
        scenarios=[dict(name=s.name, operators=s.operators, bottleneck_min=s.bottleneck_min,
                        capacity_hr=s.capacity_hr, efficiency=s.efficiency, cost=c)
                   for s, c in zip(res["scenarios"], res["costs"])],
        recommended=res["recommended"]["scn"].name, story=res["story"])
    (out / "results.json").write_text(json.dumps(_clean(summary), indent=2), encoding="utf-8")
    pdf = make_report(res, out)
    return dict(pdf=str(pdf), json=str(out / "results.json"), out_dir=str(out))

"""python -m kaarkhana analyze VIDEO --line assets/sim10_line.json --out results/"""
import argparse, sys
from . import pipeline as P, detect as D
from .config import LineConfig


def main(argv=None):
    ap = argparse.ArgumentParser(prog="kaarkhana")
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("analyze", help="analyse a line video")
    a.add_argument("video"); a.add_argument("--line", required=True, help="line config JSON")
    a.add_argument("--out", default="results")
    a.add_argument("--detector", choices=["classical", "sam3"], default="classical")
    a.add_argument("--sam-model", default="facebook/sam3")
    a.add_argument("--anchors", help="x1,y1,x2,y2 pixel centres of first and last station (if plates not auto-found)")
    a.add_argument("--hz", type=float, default=10.0); a.add_argument("--max-seconds", type=float)
    a.add_argument("--feed-rate", type=float, help="garments/hour released by cutting (caps the benefit)")
    a.add_argument("--wage", type=float); a.add_argument("--cm-usd", type=float)
    a.add_argument("--llm", action="store_true", help="polish wording with a free local LLM (numeric-guarded)")
    n = ap.parse_args(argv)

    cfg = LineConfig.load(n.line)
    if n.wage: cfg.costing.wage_bdt_per_hr = n.wage
    if n.cm_usd: cfg.costing.cm_usd_per_piece = n.cm_usd
    anchors = None
    if n.anchors:
        try:
            v = [float(x) for x in n.anchors.split(",")]
        except ValueError:
            ap.error("--anchors must be four numbers: x1,y1,x2,y2")
        if len(v) != 4:
            ap.error("--anchors must be four numbers: x1,y1,x2,y2 (got %d)" % len(v))
        anchors = ((v[0], v[1]), (v[2], v[3]))
    det = D.make_detector(n.detector, **({"model_id": n.sam_model} if n.detector == "sam3" else {}))
    agent = None
    if n.llm:
        from .agent import LocalLLMAgent
        agent = LocalLLMAgent()
    bar = lambda f: print(f"\r  analysing {f*100:3.0f}%", end="", file=sys.stderr)
    res = P.analyse(n.video, cfg, det, anchors, n.hz, bar, n.max_seconds, n.feed_rate, agent)
    print(file=sys.stderr)
    out = P.save_outputs(res, n.out)
    print(res["story"]["headline"]); print(res["story"]["prescription"]); print("report:", out["pdf"])


if __name__ == "__main__":
    main()

"""The 'IE agent': turns measurements into a justified prescription.

RuleAgent is deterministic and always available: every sentence is built from
a measured number, so there is nothing to hallucinate and nothing leaves the
machine. LocalLLMAgent optionally lets a small open model (free, runs locally
on a Colab GPU or laptop) polish the wording - but its output is rejected if
it contains any number that is not in the facts.
"""
from __future__ import annotations
import math
import re


def _f(x, d=1):
    """Format a measured number; never print nan/inf into a manager-facing report."""
    try:
        v = float(x)
    except (TypeError, ValueError):
        return "n/a"
    return f"{v:.{d}f}" if math.isfinite(v) else "n/a"


def build_facts(res) -> dict:
    c, tab, rec = res["constraint"], res["table"], res["recon"]
    sc, costs = res["scenarios"], res["costs"]
    rec_scn = res["recommended"]
    i = c.idx
    base = sc[0]
    slow_pos = int(rec["sheet_basic_s"].idxmax())
    sheet_slow = rec.iloc[slow_pos]
    return dict(
        constraint_id=c.id, constraint_name=c.name, confidence=c.confidence,
        sheet_slowest_id=str(sheet_slow["id"]), sheet_slowest_name=str(sheet_slow["name"]),
        sheet_slowest_s=float(sheet_slow.sheet_basic_s),
        ratio=c.margin, cycle_s=float(tab.cycle_med_s[i]), cycle_real_s=float(rec.observed_s[i]),
        sheet_basic_s=float(rec.sheet_basic_s[i]), line_pace=float(rec.attrs["line_pace"]),
        base_cap=base.capacity_hr, base_eff=base.efficiency * 100,
        rec_name=rec_scn["scn"].name, rec_cap=rec_scn["scn"].capacity_hr,
        rec_eff=rec_scn["scn"].efficiency * 100, rec_ops=rec_scn["scn"].extra_operators,
        net_day=rec_scn["cost"]["net_day_bdt"], net_year_usd=rec_scn["cost"]["net_year_usd"],
        extra_pcs=rec_scn["cost"]["extra_pcs_day"],
        n_visits=int(tab.visits.sum()), span_s=res["span_s"],
    )


class RuleAgent:
    name = "rule-based (deterministic)"

    def write(self, res) -> dict:
        f = build_facts(res)
        c, rec = res["constraint"], res["recon"]
        flagged = [r.id for r in rec.itertuples() if r.flag]
        headline = (f"{f['constraint_id']} {f['constraint_name']} sets the pace of this line "
                    f"(confidence: {f['confidence']}). Its bundles take {_f(f['cycle_s'])} s per cycle in the footage, "
                    f"{_f(f['ratio'])}x the median of the other stations.")
        evidence = [f"{lbl}: {'yes' if ok else 'no'} - {det}" for lbl, ok, det in c.evidence]
        if f["sheet_slowest_id"] == f["constraint_id"]:
            sheet_claim = "so the observed bottleneck agrees with the sheet"
        else:
            sheet_claim = "so the observed bottleneck has moved and needs an IE check"
        recon = (f"Against the factory's own SMV sheet, the line runs at {_f(f['line_pace'], 2)}x basic time on median. "
                 f"{f['constraint_id']} is observed at {_f(f['cycle_real_s'], 0)} s against {_f(f['sheet_basic_s'], 0)} s basic "
                 f"on the sheet. The sheet's slowest operation is {f['sheet_slowest_id']} {f['sheet_slowest_name']} "
                 f"({_f(f['sheet_slowest_s'], 0)} s basic), {sheet_claim}. ")
        recon += (f"Stations whose pace deviates more than 25% from the line pace and need an IE check: {', '.join(flagged)}."
                  if flagged else "No station deviates more than 25% from the line pace, so the SMV sheet and the footage agree.")
        rx = (f"Recommended: {f['rec_name']}. Line capacity moves from {_f(f['base_cap'])} to {_f(f['rec_cap'])} garments/hour "
              f"(theoretical) and balance efficiency from {_f(f['base_eff'], 0)}% to {_f(f['rec_eff'], 0)}%. "
              f"At the stated costing inputs and a {int(res['cfg'].costing.realisation*100)}% realisation factor this is about "
              f"{_f(f['extra_pcs'], 0)} more garments per day and BDT {f['net_day']:,.0f} net per day "
              f"(about USD {f['net_year_usd']:,.0f} per year).")
        caveat = (f"Measured from {f['n_visits']} complete bundle visits over {_f(f['span_s'], 0)} s of footage. "
                  "Visit time includes about a second of hand-off, so absolute times read slightly high; "
                  "relative comparisons between stations are the reliable part. Savings assume the cutting table can "
                  "supply the extra output and are only as good as the wage and price inputs.")
        return dict(headline=headline, evidence=evidence, recon=recon, prescription=rx, caveat=caveat, engine=self.name)


_NUM = re.compile(r"\d[\d,]*\.?\d*")


def _numbers(text):
    return {n.replace(",", "").rstrip(".") for n in _NUM.findall(text)}


class LocalLLMAgent:
    """Optional free local LLM polish with a numeric guard."""

    def __init__(self, generate=None, model="Qwen/Qwen2.5-1.5B-Instruct"):
        self.model = model
        self.name = f"local LLM ({model}) + numeric guard"
        if generate is None:
            from transformers import pipeline
            pipe = pipeline("text-generation", model=model, device_map="auto")
            generate = lambda p: pipe(p, max_new_tokens=400, do_sample=False, return_full_text=False)[0]["generated_text"]
        self.generate = generate

    def write(self, res) -> dict:
        base = RuleAgent().write(res)
        facts_text = " ".join([base["headline"], *base["evidence"], base["recon"], base["prescription"], base["caveat"]])
        prompt = ("You are an industrial engineer writing for a plant manager. Rewrite the findings below as "
                  "three short plain-English paragraphs: diagnosis, evidence, recommendation. Do not add, change "
                  "or round any number. Do not add facts.\n\nFINDINGS:\n" + facts_text + "\n\nREWRITE:")
        try:
            out = self.generate(prompt).strip()
        except Exception:
            return base
        if out and _numbers(out) <= _numbers(facts_text):
            base["narrative"] = out
            base["engine"] = self.name
        return base

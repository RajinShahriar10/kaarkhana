"""One-page-summary + evidence PDF a plant manager can review and sign."""
from __future__ import annotations
from datetime import date
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (Image, KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle)

NAVY, RED, GREY = "#143d8f", "#b42318", "#8a94a6"


def _charts(res, out: Path):
    tab, rec, ci = res["table"], res["recon"], res["constraint"].idx
    ids = tab.id.tolist()
    cols = [RED if k == ci else NAVY for k in range(len(ids))]

    fig, ax = plt.subplots(figsize=(7.2, 2.7), dpi=170)
    x = np.arange(len(ids)); w = 0.4
    ax.bar(x - w / 2, rec.observed_s, w, color=cols, label="Observed (footage)")
    ax.bar(x + w / 2, rec.sheet_basic_s, w, color="#c9d3e6", label="SMV sheet (basic)")
    ax.set_xticks(x, ids, fontsize=7); ax.set_ylabel("sec / garment", fontsize=8)
    ax.tick_params(axis="y", labelsize=7); ax.legend(fontsize=7, frameon=False)
    ax.set_title("Cycle time per station: observed vs the factory's SMV sheet", fontsize=9, loc="left")
    for s in ("top", "right"): ax.spines[s].set_visible(False)
    fig.tight_layout(); p1 = out / "chart_cycle.png"; fig.savefig(p1); plt.close(fig)

    fig, ax = plt.subplots(figsize=(7.2, 2.9), dpi=170)
    ev = res["events"]
    for _, r in ev.iterrows():
        ax.barh(r.idx, r.t_end - r.t_start, left=r.t_start, height=0.62,
                color=RED if r.idx == ci else NAVY, alpha=0.9, lw=0)
    ax.set_yticks(range(len(ids)), ids, fontsize=7); ax.invert_yaxis()
    ax.set_xlabel("video time (s)", fontsize=8); ax.tick_params(axis="x", labelsize=7)
    ax.set_title("When each station is busy with a bundle (gaps = starved or waiting)", fontsize=9, loc="left")
    for s in ("top", "right"): ax.spines[s].set_visible(False)
    fig.tight_layout(); p2 = out / "chart_timeline.png"; fig.savefig(p2); plt.close(fig)

    fig, ax = plt.subplots(figsize=(7.2, 2.3), dpi=170)
    sc = res["scenarios"]
    names = [s.name for s in sc]; caps = [s.capacity_hr for s in sc]
    ax.barh(range(len(sc)), caps, color=[GREY] + [NAVY] * (len(sc) - 1))
    ax.set_yticks(range(len(sc)), names, fontsize=7); ax.invert_yaxis()
    for k, v in enumerate(caps): ax.text(v + 0.5, k, f"{v:.0f}", va="center", fontsize=7)
    ax.set_xlabel("theoretical capacity (garments / hour)", fontsize=8); ax.tick_params(axis="x", labelsize=7)
    ax.set_title("Line capacity under each prescription", fontsize=9, loc="left")
    for s in ("top", "right"): ax.spines[s].set_visible(False)
    fig.tight_layout(); p3 = out / "chart_scenarios.png"; fig.savefig(p3); plt.close(fig)
    return p1, p2, p3


def make_report(res, out_dir) -> Path:
    out = Path(out_dir)
    cfg, c, story = res["cfg"], res["constraint"], res["story"]
    p1, p2, p3 = _charts(res, out)
    ss = getSampleStyleSheet()
    H1 = ParagraphStyle("h1", parent=ss["Title"], fontSize=18, alignment=0, spaceAfter=2, textColor=colors.HexColor(NAVY))
    H2 = ParagraphStyle("h2", parent=ss["Heading2"], fontSize=11.5, spaceBefore=9, spaceAfter=3, textColor=colors.HexColor(NAVY))
    B = ParagraphStyle("b", parent=ss["BodyText"], fontSize=9, leading=12.5)
    S = ParagraphStyle("s", parent=B, fontSize=7.5, leading=10, textColor=colors.HexColor("#555"))
    doc = SimpleDocTemplate(str(out / "kaarkhana_report.pdf"), pagesize=A4,
                            leftMargin=16 * mm, rightMargin=16 * mm, topMargin=14 * mm, bottomMargin=14 * mm,
                            title="Kaarkhana line balancing report")
    el = []
    el.append(Paragraph("Kaarkhana - Line Balancing Report", H1))
    el.append(Paragraph(f"{cfg.name} &nbsp;|&nbsp; {cfg.style} &nbsp;|&nbsp; {date.today().isoformat()} "
                        f"&nbsp;|&nbsp; analysed on-device, no footage left the machine", S))
    el.append(Spacer(1, 5))

    box = Table([[Paragraph(f"<b>Constraint: {c.id} {c.name}</b><br/>{story['headline']}", B)],
                 [Paragraph(f"<b>Prescription.</b> {story['prescription']}", B)]],
                colWidths=[178 * mm])
    box.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 1, colors.HexColor(RED)),
                             ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fdf3f2")),
                             ("LEFTPADDING", (0, 0), (-1, -1), 7), ("TOPPADDING", (0, 0), (-1, -1), 5),
                             ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]))
    el.append(box)
    if story.get("narrative"):
        el += [Paragraph("In plain words", H2), Paragraph(story["narrative"].replace("\n", "<br/>"), B)]

    el.append(Paragraph("1. Evidence the constraint is real", H2))
    for lbl, ok, det in c.evidence:
        el.append(Paragraph(f"<b>{'Yes' if ok else 'No'}</b> - {lbl}: {det}", B))
    el.append(Image(str(p1), width=178 * mm, height=178 * mm * 2.7 / 7.2))
    el.append(Image(str(p2), width=178 * mm, height=178 * mm * 2.9 / 7.2))

    el.append(Paragraph("2. Reconciled against the factory's SMV sheet", H2))
    el.append(Paragraph(story["recon"], B))
    rec = res["recon"]
    rows = [["Station", "Observed s", "Sheet basic s", "Pace x", "vs line", "Check"]]
    for r in rec.itertuples():
        rows.append([f"{r.id} {r.name}", f"{r.observed_s:.0f}", f"{r.sheet_basic_s:.0f}", f"{r.pace:.2f}",
                     f"{r.dev_vs_line_pace*100:+.0f}%", "CHECK" if r.flag else "ok"])
    t = Table(rows, colWidths=[62 * mm, 24 * mm, 26 * mm, 20 * mm, 22 * mm, 18 * mm], repeatRows=1)
    t.setStyle(TableStyle([("FONTSIZE", (0, 0), (-1, -1), 7.5), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(NAVY)),
                           ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#c9d3e6")),
                           ("BACKGROUND", (0, c.idx + 1), (-1, c.idx + 1), colors.HexColor("#fdf3f2")),
                           ("ALIGN", (1, 0), (-1, -1), "RIGHT")]))
    el.append(t)

    el.append(Paragraph("3. Rebalance options and what they are worth", H2))
    el.append(Image(str(p3), width=178 * mm, height=178 * mm * 2.3 / 7.2))
    cs = cfg.costing
    rows = [["Option", "Operators", "Bottleneck min", "Capacity /hr", "Balance eff.", "Net BDT/day", "Net USD/yr"]]
    for s, k in zip(res["scenarios"], res["costs"]):
        rows.append([s.name, str(sum(s.operators)), f"{s.bottleneck_min:.2f}", f"{s.capacity_hr:.0f}",
                     f"{s.efficiency*100:.0f}%", "-" if s.kind == "current" else f"{k['net_day_bdt']:,.0f}",
                     "-" if s.kind == "current" else f"{k['net_year_usd']:,.0f}"])
    t = Table(rows, colWidths=[50 * mm, 19 * mm, 24 * mm, 22 * mm, 21 * mm, 23 * mm, 22 * mm], repeatRows=1)
    t.setStyle(TableStyle([("FONTSIZE", (0, 0), (-1, -1), 7.5), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(NAVY)),
                           ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#c9d3e6")),
                           ("ALIGN", (1, 0), (-1, -1), "RIGHT")]))
    el.append(t)
    shift = next((s for s in res["scenarios"] if s.kind == "shift"), None)
    if shift and shift.shifted:
        ids = [x.id for x in cfg.stations]
        mv = "; ".join(f"{m:.2f} min of {ids[a]} to {ids[b]}" for a, b, m in shift.shifted)
        el.append(Paragraph(f"<b>Same-headcount option moves:</b> {mv}. {shift.note}", S))
    if res.get("smv_scenarios"):
        a, b = res["smv_scenarios"][0], next(s for s in res["smv_scenarios"] if s.kind == "add" and s.extra_operators == 1)
        el.append(Paragraph(f"Cross-check on the sheet's own standard SMV: the same +1 operator fix moves capacity "
                            f"{a.capacity_hr:.0f} to {b.capacity_hr:.0f} garments/hour.", S))

    el.append(Paragraph("4. Assumptions you can change", H2))
    el.append(Paragraph(f"Operator cost BDT {cs.wage_bdt_per_hr:.0f}/hour; cut-and-make price USD {cs.cm_usd_per_piece:.2f}/garment; "
                        f"USD 1 = BDT {cs.usd_to_bdt:.0f}; {cs.hours_per_day:.0f} h/day; {cs.days_per_year} days/year; "
                        f"{cs.realisation*100:.0f}% of theoretical capacity gain assumed realised. "
                        f"Savings assume cutting and downstream stations can absorb the extra flow. "
                        f"Edit these in the line config and re-run.", B))
    el.append(Paragraph("5. Method and limits", H2))
    el.append(Paragraph(f"Bundles are segmented from the footage ({res['detector']} detector), tracked at each station's work spot, "
                        f"and turned into an event stream: arrive, work, depart. Cycle time is how long a bundle stays; "
                        f"queue is fabric waiting upstream. {story['caveat']} Validation to date is on a simulated line "
                        f"with known cycle times (see validation report); it has not yet been validated on a live factory floor.", B))

    sig = Table([["Prepared by (IE)", "Reviewed by (Production Mgr)", "Approved by (Plant Manager)"],
                 ["\n\n_______________________", "\n\n_______________________", "\n\n_______________________"],
                 ["Name / date", "Name / date", "Name / date"]], colWidths=[59 * mm] * 3)
    sig.setStyle(TableStyle([("FONTSIZE", (0, 0), (-1, -1), 8), ("TEXTCOLOR", (0, 2), (-1, 2), colors.HexColor("#666"))]))
    el.append(Spacer(1, 12)); el.append(KeepTogether([sig]))
    el.append(Paragraph(f"Generated by Kaarkhana {__import__('kaarkhana').__version__}. Decision support: review with your industrial engineer before changing the line.", S))
    doc.build(el)
    return out / "kaarkhana_report.pdf"

import json, sys
from pathlib import Path
from types import SimpleNamespace
import numpy as np, pandas as pd, pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from kaarkhana import balance as B, analysis as A, agent as G
from kaarkhana.config import LineConfig, Costing
from kaarkhana.events import _presence, _split_by_colour, _runs

ROOT = Path(__file__).resolve().parents[1]


def test_add_operator_matches_sheet():
    # the factory sheet's own proposal: 2nd operator at ST5 lifts efficiency 52% -> 92%
    cfg = LineConfig.load(ROOT / "assets/sim10_line.json")
    work = [s.std_smv_min for s in cfg.stations]
    sc = B.scenarios(work, [1] * 10, [s.id for s in cfg.stations])
    add1 = next(s for s in sc if s.kind == "add" and s.extra_operators == 1)
    assert sc[0].bottleneck_idx == 4 and add1.operators[4] == 2
    assert abs(sc[0].efficiency - 0.5186) < 1e-3 and abs(add1.efficiency - 0.9215) < 2e-2
    assert abs(sc[0].capacity_hr - 36.40) < 0.05


def test_shift_never_exceeds_cap_and_keeps_work():
    work = [1, 1, 2, 1, 1]
    ops, per, b, eff, sh = B.shift_tasks(work, [1] * 5, cap_frac=0.3)
    assert sum(m for _, _, m in sh) <= 0.3 * 2 + 1e-9
    assert per.max() < 2


def test_shift_handles_multiple_operators_without_overshoot():
    work, ops = [2.0, 8.0, 2.0], [1, 2, 1]          # per-op loads 2, 4, 2
    ops2, per, b, eff, shifts = B.shift_tasks(work, ops)
    assert ops2 == ops and shifts
    assert sum(float(p) * o for p, o in zip(per, ops)) == pytest.approx(sum(work))
    assert per.max() <= max(np.array(work) / np.array(ops)) + 1e-9
    assert per[1] < 4.0                              # the 2-operator station improved


def test_cost_caps_at_feed():
    c = Costing()
    base = B.Scenario("c", "current", [1], [2], 0, 2, 30, .5, 0)
    s = B.Scenario("s", "add", [1, 1], [1], 0, 1, 60, .9, 1)
    capped = B.cost(s, base, 40, c)["extra_pcs_day"]
    free = B.cost(s, base, None, c)["extra_pcs_day"]
    assert capped < free


def test_presence_and_colour_split():
    a = np.r_[np.zeros(5), np.full(40, .3), np.zeros(5)]
    p = _presence(a)
    assert _runs(p) == [(5, 45)]
    lab = np.zeros((50, 3)); lab[5:25] = [60, 10, 10]; lab[25:45] = [70, -30, 40]
    parts = _split_by_colour(lab, 5, 45)
    assert len(parts) == 2


def _fake_res(sheet_basic=(0.7, 2.0, 0.7)):
    """Minimal pipeline result for the narrative agent tests."""
    ids = ["S0", "S1", "S2"]
    tab = pd.DataFrame(dict(id=ids, name=["A", "B", "C"], operators=[1, 2, 1],
                            visits=[10, 10, 10], cycle_med_s=[4.0, 9.0, 4.1],
                            cycle_per_op_s=[4.0, 4.5, 4.1]))
    rec = pd.DataFrame(dict(id=ids, name=["A", "B", "C"],
                            observed_s=[40.0, 90.0, 41.0],
                            sheet_basic_s=[v * 60 for v in sheet_basic],
                            sheet_std_s=[v * 60 * 1.15 for v in sheet_basic],
                            pace=[1.0] * 3, dev_vs_line_pace=[0.0] * 3, flag=[False] * 3))
    rec.attrs["line_pace"] = 1.0
    base = B.Scenario("Current line", "current", [1, 2, 1], [4.0, 4.5, 4.1], 1, 4.5, 60 / 4.5, .5, 0)
    rec_scn = B.Scenario("Add 1 operator", "add", [1, 3, 1], [4.0, 3.0, 4.1], 1, 4.1, 60 / 4.1, .55, 1)
    cost = dict(net_day_bdt=1000.0, net_year_usd=5000.0, extra_pcs_day=20.0)
    return dict(table=tab, recon=rec,
                constraint=A.Constraint(1, "S1", "B", "high", 1.1,
                                        [("Longest cycle per operator", True, "9.0s vs 4.0s")]),
                scenarios=[base, rec_scn], costs=[{}, cost], recommended=dict(scn=rec_scn, cost=cost, idx=1),
                span_s=100.0, cfg=SimpleNamespace(costing=Costing(realisation=0.6)))


def test_agent_numeric_guard():
    res = _fake_res()
    clean = G.RuleAgent().write(res)["headline"]           # only numbers already in the facts
    ok = G.LocalLLMAgent(generate=lambda _p: clean).write(res)
    assert ok["narrative"] == clean and "local LLM" in ok["engine"]

    invented = G.LocalLLMAgent(generate=lambda _p: "This saves 999.9 garments a day.").write(res)
    assert "narrative" not in invented and "local LLM" not in invented["engine"]


def test_agent_sheet_claim_follows_the_data():
    agrees = G.RuleAgent().write(_fake_res(sheet_basic=(0.7, 2.0, 0.7)))["recon"]
    assert "bottleneck agrees with the sheet" in agrees
    moved = G.RuleAgent().write(_fake_res(sheet_basic=(2.0, 0.7, 0.7)))["recon"]
    assert "bottleneck has moved" in moved and "S0" in moved


def test_constraint_logic_on_synthetic_table():
    n = 6
    tab = pd.DataFrame(dict(id=[f"S{i}" for i in range(n)], name=list("abcdef"), operators=1, visits=20,
                            cycle_med_s=[4, 4, 9, 4, 4, 4], busy_frac=[.8, .7, .75, .3, .3, .3],
                            queue_p90=[5, 1, 3, .2, .2, .2]))
    tab["cycle_per_op_s"] = tab.cycle_med_s
    c = A.find_constraint(tab)
    assert c.id == "S2" and c.confidence == "high"

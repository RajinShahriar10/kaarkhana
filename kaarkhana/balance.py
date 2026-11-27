"""Rebalance prescriptions and costing."""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np
from .config import Costing


@dataclass
class Scenario:
    name: str
    kind: str
    operators: list
    loads: list                 # min of work per operator, per station
    bottleneck_idx: int
    bottleneck_min: float
    capacity_hr: float
    efficiency: float           # sum(load*ops) / (ops_total * bottleneck)
    extra_operators: int
    note: str = ""
    shifted: list | None = None  # task shifts [(from, to, minutes)]


def _eval(work, ops):
    per = np.array(work) / np.array(ops)
    b = int(np.argmax(per))
    eff = float(np.sum(work) / (np.sum(ops) * per[b]))
    return per, b, eff


def add_operators(work, ops0, extra):
    ops = list(ops0)
    for _ in range(extra):
        per = np.array(work) / np.array(ops)
        ops[int(np.argmax(per))] += 1          # optimal greedy for min-max load
    per, b, eff = _eval(work, ops)
    return ops, per, b, eff


def shift_tasks(work, ops0, cap_frac=0.30, iters=200):
    """Same headcount: move part of the bottleneck operation to neighbours with slack.

    Only adjacent stations, and at most cap_frac of an operation's content is
    moved (needs method-study sign-off: which sub-operations can be moved).
    """
    w = np.array(work, float)
    ops = np.array(ops0)
    moved = np.zeros(len(w))
    shifts = []
    for _ in range(iters):
        per = w / ops
        i = int(np.argmax(per))
        nb = [j for j in (i - 1, i + 1) if 0 <= j < len(w)]
        j = min(nb, key=lambda k: per[k])
        room = cap_frac * work[i] - moved[i]
        # Moving d minutes changes per-operator load by d/ops[i] at i and d/ops[j]
        # at j. Half of the gap-closing amount keeps the step stable when either
        # station has more than one operator (the old code overshot in that case).
        gap = per[i] - per[j]
        step = 0.5 * gap / (1.0 / ops[i] + 1.0 / ops[j])
        d = min(step, room, 0.05 * work[i])
        if d <= 1e-6 or per[j] >= per[i]:
            break
        w[i] -= d; w[j] += d; moved[i] += d
        shifts.append((i, j, d))
    agg = {}
    for i, j, d in shifts:
        agg[(i, j)] = agg.get((i, j), 0) + d
    per, b, eff = _eval(w, ops)
    return list(ops), per, b, eff, [(i, j, m) for (i, j), m in agg.items()]


def scenarios(work_min, ops0, ids, max_extra=2):
    out = []
    per0, b0, eff0 = _eval(work_min, ops0)
    out.append(Scenario("Current line", "current", list(ops0), per0.tolist(), b0, float(per0[b0]),
                        60 / per0[b0], eff0, 0))
    o, per, b, eff, sh = shift_tasks(work_min, ops0)
    out.append(Scenario("Rebalance, same headcount", "shift", o, per.tolist(), b, float(per[b]),
                        60 / per[b], eff, 0,
                        "Moves part of the constraint operation to neighbouring stations with slack. "
                        "Needs a method-study check of which sub-operations can move.", sh))
    for k in range(1, max_extra + 1):
        o, per, b, eff = add_operators(work_min, ops0, k)
        out.append(Scenario(f"Add {k} operator{'s' if k > 1 else ''}", "add", o, per.tolist(), b,
                            float(per[b]), 60 / per[b], eff, k))
    return out


def cost(scn: Scenario, base: Scenario, feed_hr: float | None, c: Costing):
    """Daily / annual value of a scenario vs the current line.

    Output is capped by the feed rate (cutting table release) so we never
    promise garments the upstream cannot supply. Extra output is valued at the
    cut-and-make price; added operators cost wage x hours.
    """
    cap0 = base.capacity_hr if feed_hr is None else min(base.capacity_hr, feed_hr)
    cap1 = scn.capacity_hr if feed_hr is None else min(scn.capacity_hr, feed_hr)
    extra_pcs_day = (cap1 - cap0) * c.hours_per_day * c.realisation
    value_day = extra_pcs_day * c.cm_usd_per_piece * c.usd_to_bdt          # BDT
    labour_day = scn.extra_operators * c.wage_bdt_per_hr * c.hours_per_day
    net_day = value_day - labour_day
    ops1 = sum(scn.operators)
    lab_per_pc0 = sum(base.operators) * c.wage_bdt_per_hr / cap0 if cap0 else float("nan")
    cap1_real = cap0 + (cap1 - cap0) * c.realisation
    lab_per_pc1 = ops1 * c.wage_bdt_per_hr / cap1_real if cap1_real else float("nan")
    return dict(scenario=scn.name, output_hr=cap1_real, output_hr_base=cap0,
                extra_pcs_day=extra_pcs_day, value_day_bdt=value_day,
                labour_day_bdt=labour_day, net_day_bdt=net_day,
                net_year_bdt=net_day * c.days_per_year,
                net_year_usd=net_day * c.days_per_year / c.usd_to_bdt,
                labour_per_pc_base=lab_per_pc0, labour_per_pc=lab_per_pc1)

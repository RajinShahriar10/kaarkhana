"""Line configuration: stations, SMV standards, costing inputs."""
from __future__ import annotations
import json
from dataclasses import dataclass, field, asdict
from pathlib import Path


@dataclass
class Station:
    id: str
    name: str
    machine: str = ""
    basic_smv_min: float | None = None      # basic time per garment (min)
    std_smv_min: float | None = None        # standard SMV incl. allowance (min)
    operators: int = 1


@dataclass
class Costing:
    wage_bdt_per_hr: float = 100.0          # fully-loaded operator cost, BDT/hour (EDIT)
    cm_usd_per_piece: float = 1.00          # cut-and-make price per garment, USD (EDIT)
    usd_to_bdt: float = 122.0               # FX (EDIT)
    hours_per_day: float = 8.0
    days_per_year: int = 300
    realisation: float = 0.6                # share of theoretical capacity gain realised in practice (EDIT)


@dataclass
class LineConfig:
    name: str
    style: str
    pitch_m: float                          # distance between stations (m)
    time_scale: float = 1.0                 # real seconds per video second (sim=10)
    allowance: float = 0.15
    stations: list[Station] = field(default_factory=list)
    costing: Costing = field(default_factory=Costing)

    @classmethod
    def load(cls, path) -> "LineConfig":
        d = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(
            name=d["name"], style=d.get("style", ""), pitch_m=d["pitch_m"],
            time_scale=d.get("time_scale", 1.0), allowance=d.get("allowance", 0.15),
            stations=[Station(**s) for s in d["stations"]],
            costing=Costing(**d.get("costing", {})),
        )

    def save(self, path):
        Path(path).write_text(json.dumps(asdict(self), indent=2, ensure_ascii=False), encoding="utf-8")

    @property
    def n(self):
        return len(self.stations)

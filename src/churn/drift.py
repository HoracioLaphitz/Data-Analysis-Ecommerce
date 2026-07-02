import json
import numpy as np
import pandas as pd


class DriftMonitor:
    """Population Stability Index per feature. Portable, offline."""

    def __init__(self, reference: pd.DataFrame, bins: int = 10) -> None:
        self.bins = bins
        self._edges: dict[str, list[float]] = {}
        self._ref_pct: dict[str, list[float]] = {}
        for col in reference.columns:
            edges = np.quantile(reference[col], np.linspace(0, 1, bins + 1))
            edges[0], edges[-1] = -np.inf, np.inf
            edges = np.unique(edges)
            counts, _ = np.histogram(reference[col], bins=edges)
            pct = counts / max(counts.sum(), 1)
            self._edges[col] = edges.tolist()
            self._ref_pct[col] = pct.tolist()

    def psi(self, current: pd.DataFrame) -> dict:
        out = {}
        for col, edges in self._edges.items():
            if col not in current.columns:
                continue
            ref_pct = np.array(self._ref_pct[col])
            counts, _ = np.histogram(current[col], bins=np.array(edges))
            cur_pct = counts / max(counts.sum(), 1)
            eps = 1e-6
            ref_pct = np.clip(ref_pct, eps, None)
            cur_pct = np.clip(cur_pct, eps, None)
            out[col] = float(np.sum((cur_pct - ref_pct) * np.log(cur_pct / ref_pct)))
        return out

    def save_reference(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"bins": self.bins, "edges": self._edges,
                       "ref_pct": self._ref_pct}, f, indent=2)

    @classmethod
    def from_reference_file(cls, path: str) -> "DriftMonitor":
        with open(path, "r", encoding="utf-8") as f:
            blob = json.load(f)
        obj = cls.__new__(cls)
        obj.bins = blob["bins"]
        obj._edges = blob["edges"]
        obj._ref_pct = blob["ref_pct"]
        return obj

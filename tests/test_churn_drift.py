import numpy as np
import pandas as pd
from src.churn.drift import DriftMonitor


def _frame(seed):
    rng = np.random.default_rng(seed)
    return pd.DataFrame({
        "recency_days": rng.uniform(0, 200, 500),
        "frequency": rng.uniform(1, 20, 500),
    })


def test_psi_zero_for_same_distribution():
    ref = _frame(1)
    psi = DriftMonitor(ref).psi(ref)
    assert all(v < 0.1 for v in psi.values())


def test_psi_flags_shift():
    ref = _frame(1)
    cur = _frame(1).assign(recency_days=lambda d: d["recency_days"] + 500)
    psi = DriftMonitor(ref).psi(cur)
    assert psi["recency_days"] > 0.2


def test_reference_roundtrip(tmp_path):
    ref = _frame(1)
    path = str(tmp_path / "ref.json")
    DriftMonitor(ref).save_reference(path)
    loaded = DriftMonitor.from_reference_file(path)
    psi = loaded.psi(ref)
    assert all(v < 0.1 for v in psi.values())

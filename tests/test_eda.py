import os
import pytest


def test_profile_mart_writes_html(test_db_path, tmp_path):
    ydp = pytest.importorskip("ydata_profiling")  # skip if heavy dep absent
    from src.eda import profile_mart
    out = str(tmp_path / "eda.html")
    result = profile_mart(test_db_path, out)
    assert result == out
    assert os.path.exists(out)
    assert os.path.getsize(out) > 0

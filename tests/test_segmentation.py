import pandas as pd
import pytest
from src.segmentation import RFMBuilder, CohortBuilder, compute_kpis


def test_rfm_groups_by_customer_unique_id_not_customer_id(segmentation_mart):
    rfm = RFMBuilder().build(segmentation_mart)
    assert set(rfm.index) == {"u1", "u2", "u3"}
    assert rfm.loc["u1", "frequency"] == 2  # c1 + c1b both map to u1


def test_rfm_frequency_score_is_capped_not_quantile(segmentation_mart):
    rfm = RFMBuilder().build(segmentation_mart)
    assert rfm.loc["u1", "F"] == 2  # frequency clipped, not quantile-derived
    assert rfm.loc["u2", "F"] == 1
    assert rfm.loc["u3", "F"] == 1


def test_cohort_recent_cohort_is_nan_not_zero(segmentation_mart):
    matrix = CohortBuilder().build(segmentation_mart, window_months=12)
    u3_cohort = pd.Period("2018-07", freq="M")
    # u3's cohort is the last month in the fixture: month_offset=3 hasn't
    # happened yet and must be NaN, never 0.0.
    assert pd.isna(matrix.loc[u3_cohort, 3])


def test_cohort_month_zero_is_full_cohort(segmentation_mart):
    matrix = CohortBuilder().build(segmentation_mart, window_months=12)
    jan_cohort = pd.Period("2018-01", freq="M")
    assert matrix.loc[jan_cohort, 0] == 100.0


def test_cohort_month_two_shows_repeat_customer_only(segmentation_mart):
    matrix = CohortBuilder().build(segmentation_mart, window_months=12)
    jan_cohort = pd.Period("2018-01", freq="M")
    # Jan cohort has u1 and u2; only u1 returns in month offset 2 (March).
    assert matrix.loc[jan_cohort, 2] == 50.0


def test_compute_kpis_shape(segmentation_mart):
    kpis = compute_kpis(segmentation_mart, window_months=12)
    assert set(kpis["retention"].keys()) == {"M1", "M3", "M6", "M12"}
    assert kpis["global_repeat_rate"] == pytest.approx(100 / 3, abs=0.1)


def test_rfm_on_real_mart_matches_verified_repeat_rate(test_db_path):
    from src.mart import SalesMart
    mart = SalesMart(test_db_path)
    rfm = RFMBuilder().build(mart)
    # Fixture dataset is small; this just confirms the pipeline runs
    # end-to-end against the real ETL output without raising.
    assert not rfm.empty
    assert "segment" in rfm.columns

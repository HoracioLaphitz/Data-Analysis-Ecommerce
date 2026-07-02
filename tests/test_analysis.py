import pytest
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
from src.analysis import (run_analysis, delay_distribution, late_rate_by_state,
                          distance_delay_sample, review_distribution,
                          delay_by_review_score, monthly_aov,
                          freight_share_by_category)


def test_run_analysis_returns_dict(sample_df):
    result = run_analysis(sample_df)
    assert isinstance(result, dict)
    assert "kpis" in result
    assert "figs" in result


def test_kpis_total_revenue(sample_df):
    result = run_analysis(sample_df)
    expected = round(sample_df["payment_value"].sum(), 2)
    assert abs(result["kpis"]["total_revenue"] - expected) < 0.01


def test_kpis_total_orders(sample_df):
    result = run_analysis(sample_df)
    expected = sample_df["order_id"].nunique()
    assert result["kpis"]["total_orders"] == expected


def test_kpis_aov(sample_df):
    result = run_analysis(sample_df)
    expected = round(sample_df["payment_value"].sum() / sample_df["order_id"].nunique(), 2)
    assert abs(result["kpis"]["aov"] - expected) < 0.01


def test_figs_are_plotly_figures(sample_df):
    result = run_analysis(sample_df)
    for key in ("monthly", "categories", "states"):
        assert key in result["figs"]
        assert isinstance(result["figs"][key], go.Figure)


def test_kpis_avg_distance_km(sample_df):
    result = run_analysis(sample_df)
    expected = round(sample_df["distance_km"].mean(), 1)
    assert abs(result["kpis"]["avg_distance_km"] - expected) < 0.1


def test_kpis_avg_delivery_delay(sample_df):
    result = run_analysis(sample_df)
    expected = round(sample_df["delivery_delay_days"].mean(), 1)
    assert abs(result["kpis"]["avg_delivery_delay_days"] - expected) < 0.1


def test_kpis_late_delivery_rate(sample_df):
    result = run_analysis(sample_df)
    expected = round((sample_df["delivery_delay_days"] > 0).mean() * 100, 1)
    assert abs(result["kpis"]["late_delivery_rate"] - expected) < 0.1


def test_delay_distribution_clips_extremes(sample_df):
    df = sample_df.copy()
    df.loc[0, "delivery_delay_days"] = 500.0
    out = delay_distribution(df)
    assert out["delivery_delay_days"].max() <= 60
    assert out["delivery_delay_days"].min() >= -30
    assert len(out) == len(df)


def test_late_rate_by_state(sample_df):
    out = late_rate_by_state(sample_df)
    # sample_df: SP delay -5 (on time), RJ delay +5 (late), MG delay 0 (on time)
    rates = dict(zip(out["customer_state"], out["late_rate"]))
    assert rates["RJ"] == 100.0
    assert rates["SP"] == 0.0
    assert out.iloc[0]["customer_state"] == "RJ"  # sorted desc


def test_distance_delay_sample_deterministic_and_capped(sample_df):
    a = distance_delay_sample(sample_df, n=2, seed=42)
    b = distance_delay_sample(sample_df, n=2, seed=42)
    assert len(a) == 2
    assert a.equals(b)
    assert list(a.columns) == ["distance_km", "delivery_delay_days"]


@pytest.fixture
def insights_df():
    return pd.DataFrame({
        "order_id": ["o1", "o2", "o3", "o4"],
        "order_purchase_timestamp": [
            datetime(2018, 1, 10), datetime(2018, 1, 20),
            datetime(2018, 2, 5), datetime(2018, 2, 25),
        ],
        "payment_value": [100.0, 300.0, 200.0, 200.0],
        "freight_value": [10.0, 30.0, 40.0, 40.0],
        "review_score": [5.0, 5.0, 1.0, 3.0],
        "delivery_delay_days": [-2.0, -1.0, 10.0, 0.0],
        "product_category_name_english": ["books", "books", "toys", "toys"],
    })


def test_review_distribution(insights_df):
    out = review_distribution(insights_df)
    counts = dict(zip(out["review_score"], out["orders"]))
    assert counts == {1: 1, 3: 1, 5: 2}


def test_delay_by_review_score(insights_df):
    out = delay_by_review_score(insights_df)
    avg = dict(zip(out["review_score"], out["avg_delay"]))
    assert avg[5] == -1.5
    assert avg[1] == 10.0


def test_monthly_aov(insights_df):
    out = monthly_aov(insights_df)
    aov = dict(zip(out["month"], out["aov"]))
    assert aov["2018-01"] == 200.0  # (100+300)/2
    assert aov["2018-02"] == 200.0  # (200+200)/2
    assert list(out["month"]) == ["2018-01", "2018-02"]


def test_freight_share_by_category(insights_df):
    out = freight_share_by_category(insights_df, top=10)
    share = dict(zip(out["product_category_name_english"], out["freight_share"]))
    assert share["books"] == 10.0   # 40/400
    assert share["toys"] == 20.0    # 80/400
    assert out.iloc[0]["product_category_name_english"] == "toys"  # sorted desc


def test_freight_share_respects_top(insights_df):
    out = freight_share_by_category(insights_df, top=1)
    assert len(out) == 1

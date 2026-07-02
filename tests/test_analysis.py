import pytest
import plotly.graph_objects as go
from src.analysis import run_analysis


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


from src.analysis import (delay_distribution, late_rate_by_state,
                          distance_delay_sample)


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

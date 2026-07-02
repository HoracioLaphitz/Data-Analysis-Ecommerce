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

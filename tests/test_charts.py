import pytest
import pandas as pd
from plotly.graph_objects import Figure
from src.charts import bar_chart, line_chart, states_bar_chart


def test_bar_chart_returns_figure(sample_df):
    top = sample_df.groupby("product_category_name_english")["payment_value"].sum().reset_index()
    fig = bar_chart(top, x="product_category_name_english", y="payment_value", title="Test")
    assert isinstance(fig, Figure)


def test_bar_chart_has_data(sample_df):
    top = sample_df.groupby("product_category_name_english")["payment_value"].sum().reset_index()
    fig = bar_chart(top, x="product_category_name_english", y="payment_value", title="Test")
    assert len(fig.data) > 0


def test_line_chart_returns_figure(sample_df):
    monthly = sample_df.copy()
    monthly["month"] = monthly["order_purchase_timestamp"].dt.to_period("M").astype(str)
    agg = monthly.groupby("month")["payment_value"].sum().reset_index()
    fig = line_chart(agg, x="month", y="payment_value", title="Monthly")
    assert isinstance(fig, Figure)


def test_states_bar_chart_returns_figure(sample_df):
    by_state = sample_df.groupby("customer_state")["payment_value"].sum().reset_index()
    fig = states_bar_chart(by_state, state_col="customer_state", value_col="payment_value", title="States")
    assert isinstance(fig, Figure)


def test_feature_importance_chart():
    import plotly.graph_objects as go
    from src.charts import feature_importance_chart
    fig = feature_importance_chart({"pct_late": 0.4, "recency_days": 0.6})
    assert isinstance(fig, go.Figure)


def test_confusion_matrix_chart():
    import plotly.graph_objects as go
    from src.charts import confusion_matrix_chart
    fig = confusion_matrix_chart([[10, 2], [3, 5]])
    assert isinstance(fig, go.Figure)


def test_histogram_chart_returns_figure(sample_df):
    from src.charts import histogram_chart
    fig = histogram_chart(sample_df, x="delivery_delay_days", title="Delays")
    assert isinstance(fig, Figure)


def test_scatter_chart_returns_figure(sample_df):
    from src.charts import scatter_chart
    fig = scatter_chart(sample_df, x="distance_km", y="delivery_delay_days", title="Distance vs delay")
    assert isinstance(fig, Figure)

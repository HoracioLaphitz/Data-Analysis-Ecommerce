import plotly.express as px
import pandas as pd
from plotly.graph_objects import Figure


def bar_chart(df: pd.DataFrame, x: str, y: str, title: str) -> Figure:
    fig = px.bar(df, x=x, y=y, title=title, color=y,
                 color_continuous_scale="Blues")
    fig.update_layout(showlegend=False, coloraxis_showscale=False,
                      plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
    return fig


def line_chart(df: pd.DataFrame, x: str, y: str, title: str) -> Figure:
    fig = px.line(df, x=x, y=y, title=title, markers=True)
    fig.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
    return fig


def states_bar_chart(df: pd.DataFrame, state_col: str, value_col: str, title: str) -> Figure:
    return bar_chart(
        df.sort_values(value_col, ascending=False),
        x=state_col,
        y=value_col,
        title=title,
    )

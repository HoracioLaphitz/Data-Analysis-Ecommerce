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


def heatmap_chart(matrix: pd.DataFrame, title: str) -> Figure:
    fig = px.imshow(
        matrix,
        labels=dict(x="Meses desde primera compra", y="Cohorte", color="Retención %"),
        color_continuous_scale="Blues",
        title=title,
        text_auto=".1f",
    )
    fig.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
    return fig


def histogram_chart(df: pd.DataFrame, x: str, title: str) -> Figure:
    fig = px.histogram(df, x=x, title=title, color_discrete_sequence=["#1f77b4"])
    fig.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                      showlegend=False)
    return fig


def scatter_chart(df: pd.DataFrame, x: str, y: str, title: str) -> Figure:
    fig = px.scatter(df, x=x, y=y, title=title, opacity=0.3)
    fig.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
    return fig


def feature_importance_chart(importance: dict) -> Figure:
    items = sorted(importance.items(), key=lambda kv: kv[1])
    df = pd.DataFrame(items, columns=["feature", "importance"])
    fig = px.bar(df, x="importance", y="feature", orientation="h",
                 title="Importancia de variables", color="importance",
                 color_continuous_scale="Blues",
                 labels=dict(importance="Importancia", feature="Variable"))
    fig.update_layout(showlegend=False, coloraxis_showscale=False,
                      plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
    return fig


def confusion_matrix_chart(matrix) -> Figure:
    fig = px.imshow(
        matrix,
        x=["Predicho: activo", "Predicho: abandonó"],
        y=["Real: activo", "Real: abandonó"],
        color_continuous_scale="Blues",
        text_auto=True,
        title="Matriz de confusión",
    )
    fig.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
    return fig

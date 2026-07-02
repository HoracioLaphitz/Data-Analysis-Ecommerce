import json
import os
import streamlit as st
from src.loader import load_data
from src.analysis import (run_analysis, delay_distribution, late_rate_by_state,
                          distance_delay_sample, review_distribution,
                          delay_by_review_score, monthly_aov,
                          freight_share_by_category)
from src.charts import (bar_chart, line_chart, histogram_chart, scatter_chart,
                        feature_importance_chart, confusion_matrix_chart,
                        heatmap_chart)
from src.mart import SalesMart
from src.segmentation import RFMBuilder, CohortBuilder, compute_kpis

DB_PATH = os.path.join("data", "olist_mart.db")

st.set_page_config(
    page_title="AI Sales Assistant",
    page_icon="🫡",
    layout="wide",
)

st.title("🤖 AI Sales Assistant")
st.caption(
    "Olist Brazilian E-Commerce · Analytics & Churn Prediction · "
    "[Code on GitHub](https://github.com/HoracioLaphitz/ai-sales-assistant)"
)

if not os.path.exists(DB_PATH):
    st.error(
        "❌ Data mart not found. "
        "Run `python -m src.etl` once to build it before starting the app."
    )
    st.stop()


@st.cache_data
def get_data():
    return load_data(DB_PATH)


@st.cache_data
def get_analysis(_df):
    return run_analysis(_df)


@st.cache_data
def get_segmentation(window_months):
    mart = SalesMart(DB_PATH)
    rfm = RFMBuilder().build(mart)
    cohorts = CohortBuilder().build(mart, window_months=window_months)
    kpis = compute_kpis(mart, window_months=window_months)
    return rfm, cohorts, kpis


MODELS_DIR = "models"


@st.cache_resource
def get_churn_artifacts():
    from src.churn.model import ChurnModel
    model = ChurnModel.load(os.path.join(MODELS_DIR, "model.pkl"))
    with open(os.path.join(MODELS_DIR, "metrics.json"), encoding="utf-8") as f:
        metrics = json.load(f)
    with open(os.path.join(MODELS_DIR, "feature_importance.json"), encoding="utf-8") as f:
        importance = json.load(f)
    return model, metrics, importance


@st.cache_data
def get_at_risk_sellers():
    from src.churn.predict import ChurnScorer
    from src.churn.recommendations import RecommendationEngine
    model, _, _ = get_churn_artifacts()
    mart = SalesMart(DB_PATH)
    scorer = ChurnScorer(model, RecommendationEngine())
    return scorer.at_risk(mart, mart.max_order_date)


with st.spinner("Loading Olist data (~100k orders)..."):
    df = get_data()

analysis = get_analysis(df)
kpis = analysis["kpis"]
figs = analysis["figs"]

tab_analysis, tab_logistics, tab_reviews, tab_churn, tab_sales, tab_seg = st.tabs([
    "📊 Analysis", "🚚 Logística", "⭐ Reviews",
    "📉 Churn Sellers", "💰 Ventas", "🧩 Segmentación",
])

with tab_analysis:
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Revenue", f"R$ {kpis['total_revenue']:,.0f}")
    col2.metric("Delivered Orders", f"{kpis['total_orders']:,}")
    col3.metric("Average Order Value", f"R$ {kpis['aov']:,.2f}")

    col4, col5, col6 = st.columns(3)
    col4.metric("Avg Distance (km)", f"{kpis['avg_distance_km']:,.1f}")
    delay = kpis["avg_delivery_delay_days"]
    col5.metric("Avg Delivery Delay", f"{'+' if delay > 0 else ''}{delay:.1f} days")
    col6.metric("Late Delivery Rate", f"{kpis['late_delivery_rate']:.1f}%")

    st.divider()

    st.plotly_chart(figs["monthly"], use_container_width=True)

    col_a, col_b = st.columns(2)
    with col_a:
        st.plotly_chart(figs["categories"], use_container_width=True)
    with col_b:
        st.plotly_chart(figs["states"], use_container_width=True)

with tab_logistics:
    st.plotly_chart(
        histogram_chart(delay_distribution(df), x="delivery_delay_days",
                        title="Distribución de demora de entrega (días)"),
        use_container_width=True)
    col_a, col_b = st.columns(2)
    with col_a:
        st.plotly_chart(
            bar_chart(late_rate_by_state(df), x="customer_state", y="late_rate",
                      title="Tasa de entregas tardías por estado (%)"),
            use_container_width=True)
    with col_b:
        st.plotly_chart(
            scatter_chart(distance_delay_sample(df), x="distance_km",
                          y="delivery_delay_days",
                          title="Distancia vs demora (muestra 5k)"),
            use_container_width=True)

with tab_reviews:
    col_a, col_b = st.columns(2)
    with col_a:
        st.plotly_chart(
            bar_chart(review_distribution(df), x="review_score", y="orders",
                      title="Distribución de review scores"),
            use_container_width=True)
    with col_b:
        st.plotly_chart(
            bar_chart(delay_by_review_score(df), x="review_score", y="avg_delay",
                      title="Demora promedio por review score (días)"),
            use_container_width=True)

with tab_churn:
    if not os.path.exists(os.path.join(MODELS_DIR, "model.pkl")):
        st.warning(
            "⚠️ Churn model not trained. Run `python -m src.churn.train` "
            "once, then reload this page."
        )
    else:
        _, metrics, importance = get_churn_artifacts()
        xgb = metrics["xgboost"]
        col1, col2, col3 = st.columns(3)
        col1.metric("AUC-ROC", f"{xgb['auc_roc']:.3f}")
        col2.metric("Recall", f"{xgb['recall']:.3f}")
        col3.metric("Churn rate", f"{metrics['churn_rate']*100:.1f}%")

        col_a, col_b = st.columns(2)
        with col_a:
            st.plotly_chart(feature_importance_chart(importance),
                            use_container_width=True)
        with col_b:
            st.plotly_chart(confusion_matrix_chart(xgb["confusion_matrix"]),
                            use_container_width=True)

        st.subheader("Top 20 sellers en riesgo")
        at_risk = get_at_risk_sellers().head(20).copy()
        at_risk["recommendations"] = at_risk["recommendations"].str.join(" · ")
        st.dataframe(at_risk, use_container_width=True)

with tab_sales:
    st.plotly_chart(
        line_chart(monthly_aov(df), x="month", y="aov",
                   title="Ticket promedio mensual — AOV (R$)"),
        use_container_width=True)
    st.plotly_chart(
        bar_chart(freight_share_by_category(df),
                  x="product_category_name_english", y="freight_share",
                  title="Peso del flete sobre el ticket por categoría (%)"),
        use_container_width=True)

with tab_seg:
    window = st.radio(
        "Ventana de retención", [6, 12], index=1,
        horizontal=True, format_func=lambda m: f"{m} meses",
    )
    with st.spinner("Calculando segmentación..."):
        rfm, cohorts, kpis_seg = get_segmentation(window)

    st.caption(
        "Solo 3.12% de los clientes de Olist repite compra — "
        "la retención y los segmentos reflejan ese comportamiento real, "
        "no un error de cálculo."
    )

    col1, col2, col3 = st.columns(3)
    col1.metric("Tasa de repetición global", f"{kpis_seg['global_repeat_rate']}%")
    col2.metric("Revenue en riesgo (At Risk + Hibernating)", f"R$ {kpis_seg['risk_segment_revenue']:,.0f}")
    m3_val = kpis_seg["retention"].get("M3")
    col3.metric("Retención M3 promedio", f"{m3_val}%" if m3_val is not None else "N/A")

    st.divider()

    cohorts_display = cohorts.copy()
    cohorts_display.index = cohorts_display.index.astype(str)
    st.plotly_chart(
        heatmap_chart(cohorts_display, f"Retención por cohorte mensual ({window} meses)"),
        use_container_width=True,
    )

    st.divider()

    segment_table = rfm["segment"].value_counts().reset_index()
    segment_table.columns = ["Segmento", "Clientes"]
    segment_table["% Revenue"] = segment_table["Segmento"].map(kpis_seg["revenue_pct_by_segment"])
    st.dataframe(segment_table, use_container_width=True)

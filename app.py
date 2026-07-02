import os
import streamlit as st
from src.loader import load_data
from src.analysis import run_analysis
from src.mart import SalesMart
from src.segmentation import RFMBuilder, CohortBuilder, compute_kpis
from src.charts import heatmap_chart

DB_PATH = os.path.join("data", "olist_mart.db")

st.set_page_config(
    page_title="AI Sales Assistant",
    page_icon="🫡",
    layout="wide",
)

st.title("🤖 AI Sales Assistant")
st.caption(
    "Olist Brazilian E-Commerce · LangChain + NVIDIA NIM · "
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


with st.spinner("Loading Olist data (~100k orders)..."):
    df = get_data()

analysis = get_analysis(df)
kpis = analysis["kpis"]
figs = analysis["figs"]

tab1, tab3 = st.tabs(["📊 Analysis", "🧩 Segmentación"])

with tab1:
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

with tab3:
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

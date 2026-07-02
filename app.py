import os
import streamlit as st
from dotenv import load_dotenv
from src.loader import load_data
from src.analysis import run_analysis
from src.agent import build_agent, ask

load_dotenv()

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


@st.cache_resource
def get_agent(_df, api_key):
    return build_agent(_df, api_key)


api_key = os.environ.get("NVAPI", "")

if not api_key:
    st.error("❌ NVAPI not found. Set the NVAPI environment variable before running the app.")
    st.stop()

with st.spinner("Loading Olist data (~100k orders)..."):
    df = get_data()

analysis = get_analysis(df)
kpis = analysis["kpis"]
figs = analysis["figs"]

tab1, tab2 = st.tabs(["📊 Analysis", "💬 Questions"])

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

with tab2:
    st.markdown("**Ask the assistant about the sales data:**")

    example_questions = [
        "Which month had the most revenue?",
        "What are the 5 states with the most orders?",
        "What is the average order value per product category?",
        "What percentage of orders had prices above R$ 200?",
    ]
    with st.expander("💡 Example questions"):
        for q in example_questions:
            st.markdown(f"- {q}")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Type your question..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Analyzing..."):
                agent = get_agent(df, api_key)
                result = ask(agent, prompt)

            st.markdown(result["answer"])

            if result["intermediate_steps"]:
                with st.expander("🔍 View generated Pandas code"):
                    for action, observation in result["intermediate_steps"]:
                        if hasattr(action, "tool_input"):
                            st.code(action.tool_input, language="python")
                        st.markdown(f"**Result:** `{str(observation)[:200]}`")

        st.session_state.messages.append({"role": "assistant", "content": result["answer"]})

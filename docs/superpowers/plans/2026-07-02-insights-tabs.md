# Insights Tabs Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove the NVIDIA NIM chat entirely and add four analytics tabs (Logística, Reviews, Churn Sellers, Ventas) built from the already-loaded orders DataFrame plus the trained churn model artifacts.

**Architecture:** Approach A from the spec — pure aggregation functions in `src/analysis.py`, pure figure builders in `src/charts.py`, `app.py` only wires tabs. The Churn tab reads `models/*.json` artifacts and scores sellers via the existing `ChurnScorer`; it degrades to a warning when `models/model.pkl` is missing.

**Tech Stack:** pandas, Plotly (`px`), Streamlit, existing `src/churn/` pipeline (XGBoost).

## Global Constraints

- `SalesMart` stays the only runtime SQL boundary; new code consumes the `df` from `load_data` or existing mart methods — no raw `sqlite3`.
- No changes to `src/etl.py`, `sql/`, `src/mart.py`, `src/churn/` logic, or the Segmentación tab.
- Code style: match `src/analysis.py` — plain functions, light type hints, no docstrings on small helpers.
- Verified facts: `metrics.json` contains `metrics["xgboost"]["confusion_matrix"]` (2×2 list) — written by `ChurnModel.evaluate` (`src/churn/model.py:52`). `ChurnModel.load(path)` is a classmethod. `RecommendationEngine()` takes no args. `SalesMart.max_order_date` is a **property**. `.gitignore` already excludes `models/*.pkl` and `models/*.json`.
- Final suite must be 100% green — including the two currently-failing tests in `tests/test_charts.py`.

---

### Task 1: Remove the LLM agent completely

**Files:**
- Delete: `src/agent.py`, `tests/test_agent.py`
- Modify: `app.py`, `Pipfile`, `requirements.txt`

**Interfaces:**
- Produces: `app.py` with only `tab1` (Analysis) and `tab3`→renamed flow intact; later tasks re-add tabs. After this task the app must boot with no `NVAPI` env var.

- [ ] **Step 1: Delete agent files**

```bash
git rm src/agent.py tests/test_agent.py
```

- [ ] **Step 2: Strip `app.py`**

Remove these pieces:
- Line 3: `from dotenv import load_dotenv` and line 8: `load_dotenv()`
- Line 6: `from src.agent import build_agent, ask`
- The `get_agent` cached function
- The `api_key = os.environ.get("NVAPI", "")` block and its `st.error`/`st.stop()`
- Replace the tabs line with `tab1, tab3 = st.tabs(["📊 Analysis", "🧩 Segmentación"])` (temporary — Task 5 rewires)
- Delete the whole `with tab2:` block (chat UI)

- [ ] **Step 3: Remove dependencies**

In `Pipfile` `[packages]`, delete the lines for `langchain`, `langchain-experimental`, `langchain-groq`, `groq`, `tabulate`, `python-dotenv`.
In `requirements.txt`, delete the lines `langchain>=0.2.0`, `langchain-experimental>=0.0.60`, `langchain-nvidia-ai-endpoints>=0.3.0`, `tabulate>=0.9.0`, `python-dotenv`.

- [ ] **Step 4: Verify**

Run: `python -m pytest tests/ -q`
Expected: no test errors from missing agent (only the 2 known `test_charts.py` failures remain).
Run: `python -c "import ast; ast.parse(open('app.py', encoding='utf-8').read())"`
Expected: no output.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat(app)!: remove NVIDIA NIM chat and langchain dependencies"
```

---

### Task 2: Logística aggregations in `src/analysis.py`

**Files:**
- Modify: `src/analysis.py` (append functions)
- Test: `tests/test_analysis.py` (append)

**Interfaces:**
- Produces:
  - `delay_distribution(df) -> pd.DataFrame` — columns `delivery_delay_days` (clipped to [-30, 60]), one row per order.
  - `late_rate_by_state(df) -> pd.DataFrame` — columns `customer_state`, `late_rate` (float %, sorted desc).
  - `distance_delay_sample(df, n=5000, seed=42) -> pd.DataFrame` — columns `distance_km`, `delivery_delay_days`, at most `n` rows, deterministic.

- [ ] **Step 1: Append failing tests to `tests/test_analysis.py`**

```python
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
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_analysis.py -q`
Expected: FAIL with `ImportError: cannot import name 'delay_distribution'`

- [ ] **Step 3: Append implementations to `src/analysis.py`**

```python
def delay_distribution(df: pd.DataFrame) -> pd.DataFrame:
    return df[["delivery_delay_days"]].assign(
        delivery_delay_days=df["delivery_delay_days"].clip(-30, 60))


def late_rate_by_state(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.assign(late=df["delivery_delay_days"] > 0)
        .groupby("customer_state")["late"].mean().mul(100).round(1)
        .reset_index()
        .rename(columns={"late": "late_rate"})
        .sort_values("late_rate", ascending=False)
        .reset_index(drop=True)
    )


def distance_delay_sample(df: pd.DataFrame, n: int = 5000, seed: int = 42) -> pd.DataFrame:
    cols = df[["distance_km", "delivery_delay_days"]]
    if len(cols) <= n:
        return cols.reset_index(drop=True)
    return cols.sample(n, random_state=seed).reset_index(drop=True)
```

- [ ] **Step 4: Run to verify pass**

Run: `python -m pytest tests/test_analysis.py -q`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add src/analysis.py tests/test_analysis.py
git commit -m "feat(analysis): add logistics aggregations"
```

---

### Task 3: Reviews + Ventas aggregations in `src/analysis.py`

**Files:**
- Modify: `src/analysis.py` (append functions)
- Test: `tests/test_analysis.py` (append)

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces:
  - `review_distribution(df) -> pd.DataFrame` — columns `review_score` (int 1–5), `orders` (count), sorted by score.
  - `delay_by_review_score(df) -> pd.DataFrame` — columns `review_score`, `avg_delay` (float), sorted by score.
  - `monthly_aov(df) -> pd.DataFrame` — columns `month` (str "YYYY-MM"), `aov` (float), sorted by month.
  - `freight_share_by_category(df, top=10) -> pd.DataFrame` — columns `product_category_name_english`, `freight_share` (float %, freight/payment × 100), top-N categories by revenue, sorted desc by share.

- [ ] **Step 1: Append failing tests to `tests/test_analysis.py`**

Note: `sample_df` has no `review_score` column, so these tests use a local fixture.

```python
import pandas as pd
from datetime import datetime
from src.analysis import (review_distribution, delay_by_review_score,
                          monthly_aov, freight_share_by_category)


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
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_analysis.py -q`
Expected: FAIL with `ImportError: cannot import name 'review_distribution'`

- [ ] **Step 3: Append implementations to `src/analysis.py`**

```python
def review_distribution(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.dropna(subset=["review_score"])
        .astype({"review_score": int})
        .groupby("review_score")["order_id"].count()
        .reset_index()
        .rename(columns={"order_id": "orders"})
        .sort_values("review_score")
        .reset_index(drop=True)
    )


def delay_by_review_score(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.dropna(subset=["review_score"])
        .astype({"review_score": int})
        .groupby("review_score")["delivery_delay_days"].mean()
        .reset_index()
        .rename(columns={"delivery_delay_days": "avg_delay"})
        .sort_values("review_score")
        .reset_index(drop=True)
    )


def monthly_aov(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.assign(month=df["order_purchase_timestamp"].dt.to_period("M").astype(str))
        .groupby("month")
        .agg(revenue=("payment_value", "sum"), orders=("order_id", "nunique"))
        .assign(aov=lambda d: (d["revenue"] / d["orders"]).round(2))
        .reset_index()[["month", "aov"]]
        .sort_values("month")
        .reset_index(drop=True)
    )


def freight_share_by_category(df: pd.DataFrame, top: int = 10) -> pd.DataFrame:
    agg = (
        df.groupby("product_category_name_english")
        .agg(revenue=("payment_value", "sum"), freight=("freight_value", "sum"))
    )
    top_cats = agg.nlargest(top, "revenue")
    return (
        top_cats.assign(freight_share=(top_cats["freight"] / top_cats["revenue"] * 100).round(1))
        .reset_index()[["product_category_name_english", "freight_share"]]
        .sort_values("freight_share", ascending=False)
        .reset_index(drop=True)
    )
```

- [ ] **Step 4: Run to verify pass**

Run: `python -m pytest tests/test_analysis.py -q`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add src/analysis.py tests/test_analysis.py
git commit -m "feat(analysis): add reviews and sales aggregations"
```

---

### Task 4: New chart builders in `src/charts.py`

**Files:**
- Modify: `src/charts.py` (append functions)
- Test: `tests/test_charts.py` (two failing tests already exist; append two smoke tests)

**Interfaces:**
- Produces:
  - `histogram_chart(df, x, title) -> Figure`
  - `scatter_chart(df, x, y, title) -> Figure`
  - `feature_importance_chart(importance: dict) -> Figure` — exact signature required by existing `tests/test_charts.py::test_feature_importance_chart` (called as `feature_importance_chart({"pct_late": 0.4, "recency_days": 0.6})`).
  - `confusion_matrix_chart(matrix) -> Figure` — exact signature required by existing `tests/test_charts.py::test_confusion_matrix_chart` (called as `confusion_matrix_chart([[10, 2], [3, 5]])`).

- [ ] **Step 1: Append smoke tests for the two generic builders to `tests/test_charts.py`**

```python
def test_histogram_chart_returns_figure(sample_df):
    from src.charts import histogram_chart
    fig = histogram_chart(sample_df, x="delivery_delay_days", title="Delays")
    assert isinstance(fig, Figure)


def test_scatter_chart_returns_figure(sample_df):
    from src.charts import scatter_chart
    fig = scatter_chart(sample_df, x="distance_km", y="delivery_delay_days", title="Distance vs delay")
    assert isinstance(fig, Figure)
```

- [ ] **Step 2: Run to verify 4 failures**

Run: `python -m pytest tests/test_charts.py -q`
Expected: 4 failed (`feature_importance`, `confusion_matrix`, `histogram`, `scatter`), rest pass.

- [ ] **Step 3: Append implementations to `src/charts.py`**

```python
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
                 title="Feature importance", color="importance",
                 color_continuous_scale="Blues")
    fig.update_layout(showlegend=False, coloraxis_showscale=False,
                      plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
    return fig


def confusion_matrix_chart(matrix) -> Figure:
    fig = px.imshow(
        matrix,
        x=["Pred: active", "Pred: churned"],
        y=["Real: active", "Real: churned"],
        color_continuous_scale="Blues",
        text_auto=True,
        title="Confusion matrix",
    )
    fig.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
    return fig
```

- [ ] **Step 4: Run to verify all pass**

Run: `python -m pytest tests/test_charts.py -q`
Expected: all pass — including the two previously-failing tests.

- [ ] **Step 5: Commit**

```bash
git add src/charts.py tests/test_charts.py
git commit -m "feat(charts): add histogram, scatter, feature importance and confusion matrix builders"
```

---

### Task 5: Wire the four tabs in `app.py` + train the model

**Files:**
- Modify: `app.py`

**Interfaces:**
- Consumes: everything from Tasks 2–4, plus `ChurnModel.load` (classmethod, `src/churn/model.py:69`), `ChurnScorer(model, engine).at_risk(mart, cutoff)` (`src/churn/predict.py:15`), `RecommendationEngine()` (no args), `SalesMart.max_order_date` (property).

- [ ] **Step 1: Train the churn model once (artifacts are gitignored)**

Run: `python -m src.churn.train`
Expected: prints `XGBoost AUC: 0.xxx | baseline AUC: 0.xxx`; `models/model.pkl`, `models/metrics.json`, `models/feature_importance.json` exist.

- [ ] **Step 2: Rewrite `app.py` imports and loaders**

Imports block becomes:

```python
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
```

After `get_segmentation`, add:

```python
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
```

- [ ] **Step 3: Rewire the tabs**

```python
tab_analysis, tab_logistics, tab_reviews, tab_churn, tab_sales, tab_seg = st.tabs([
    "📊 Analysis", "🚚 Logística", "⭐ Reviews",
    "📉 Churn Sellers", "💰 Ventas", "🧩 Segmentación",
])
```

Keep the existing Analysis content under `tab_analysis` and the existing Segmentación content under `tab_seg` (rename the `with tab1:` / `with tab3:` blocks).

- [ ] **Step 4: Add the four new tab bodies**

```python
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
```

- [ ] **Step 5: Smoke test**

Run: `python -c "import ast; ast.parse(open('app.py', encoding='utf-8').read())"` — no output.
Run: `streamlit run app.py` and verify: 6 tabs render, no traceback in any tab, Churn tab shows metrics + charts + table.

- [ ] **Step 6: Full suite**

Run: `python -m pytest tests/ -q`
Expected: 100% green, 0 failures.

- [ ] **Step 7: Commit**

```bash
git add app.py
git commit -m "feat(app): add logistics, reviews, churn and sales tabs"
```

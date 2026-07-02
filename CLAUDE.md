# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

AI Sales Assistant — a Streamlit app for natural-language Q&A and analytics over the Olist Brazilian E-Commerce dataset (~100k orders), plus a seller churn-prediction pipeline (XGBoost + rules-based recommendations).

## Commands

```bash
# Install deps (Pipenv is the source of truth; requirements.txt exists for Streamlit Cloud deploy)
pipenv install
# or: pip install -r requirements.txt

# One-time: build the SQLite data mart from raw Kaggle CSVs in data/
python -m src.etl

# Run the app (requires NVAPI env var — NVIDIA NIM API key)
streamlit run app.py

# Train the churn model (requires the data mart to exist)
python -m src.churn.train

# Tests
pytest tests/ -v
pytest tests/test_mart.py -v          # single file
pytest tests/test_mart.py::test_name  # single test
```

Note: `Pipfile` currently lists `langchain-groq`/`groq` under `[packages]`, but the actual code (`src/agent.py`) imports `langchain_nvidia_ai_endpoints`, which is only declared in `requirements.txt`. If `pipenv install` leaves `ChatNVIDIA` unavailable, install `langchain-nvidia-ai-endpoints` manually or use `requirements.txt`.

## Architecture

Two independent pipelines share one SQLite data mart (`data/olist_mart.db`), never the raw CSVs directly.

### 1. ETL → Data Mart (`src/etl.py`)

`build_mart()` runs a fixed sequence against a fresh SQLite connection:
1. Ingest 9 raw Olist CSVs into `raw_*` tables verbatim (`pandas.to_sql`).
2. `sql/clean.sql` — raw → `stg_*` staging tables (typing, dedup, filters).
3. `_enrich_distance()` — pulls `stg_orders`/`stg_order_items`/`stg_customers`/`stg_sellers` into pandas, computes Haversine `distance_km` seller↔customer, writes back as `stg_order_distance`. This is the one enrichment step done in Python instead of SQL — SQLite has no trig functions.
4. `sql/mart.sql` — staging → star schema: `fact_orders` + `dim_customers`/`dim_sellers`/`dim_products`/`dim_date`.
5. `sql/quality.sql` — gate. Each `-- CHECK: name` block must return zero rows or `build_mart()` raises `DataQualityError` (`src/errors.py`) and the mart is not considered valid.
6. `sql/views.sql` — analytical views, notably `v_seller_features` (used by churn feature building) and `v_monthly_revenue`/`v_state_revenue`.

Schema reference: `docs/data-dictionary.md`.

Run this once per dataset change; the app and churn pipeline only ever read from the built `.db` file.

### 2. Runtime read boundary (`src/mart.py`)

`SalesMart` is the **only** place that writes raw SQL against the mart at runtime. It always returns DataFrames, never connections/cursors. `src/loader.py`, `src/analysis.py`, and the churn modules all go through it — don't reach for `sqlite3` directly outside `etl.py`/`mart.py`.

### 3. Streamlit app (`app.py` → `src/analysis.py`, `src/charts.py`, `src/agent.py`)

- `analysis.run_analysis(df)` computes KPIs and builds the three Plotly figures shown in the "Analysis" tab.
- `agent.build_agent(df, api_key)` wraps `langchain_experimental`'s pandas dataframe agent around `ChatNVIDIA` (`meta/llama-3.3-70b-instruct`) with a Spanish-language system prefix, driving the "Questions" chat tab. `allow_dangerous_code=True` is required by that agent (it executes generated pandas code) — this app is a portfolio/demo project, not a treat-input-as-hostile service.
- Both `df` (from `load_data`) and the built agent are `st.cache_data`/`st.cache_resource`-wrapped in `app.py`.

### 4. Churn pipeline (`src/churn/`)

Pipeline order, each stage consuming the previous:
1. `labeling.ChurnLabeler` — picks a `cutoff` = `max_order_date - horizon_days` (default 90d), labels sellers active before cutoff as churned (0) or not (1) based on whether they have any order in the following horizon window. Sellers with no activity before cutoff are excluded entirely (not just labeled negative) — this is the leakage guard.
2. `features.SellerFeatureBuilder` — builds the seller × feature matrix using **only** orders `<= cutoff` (same leakage discipline). Feature list is the class attribute `FEATURES`; features and labels are joined on `seller_id` before training.
3. `model.ChurnModel` — one interface wrapping either `logreg` (StandardScaler + LogisticRegression, class-balanced) or `xgboost` (with `scale_pos_weight` computed from the training split). `train.py` always fits both and keeps XGBoost as the saved model; logreg only serves as a reported baseline metric.
4. `drift.DriftMonitor` — Population Stability Index per feature against a saved reference distribution (`models/drift_reference.json`), for detecting feature drift on future scoring runs — no external monitoring dependency.
5. `recommendations.RecommendationEngine` + `predict.ChurnScorer` — turns model probabilities into a ranked at-risk seller list, each with rule-based, offline-computed recommendation strings (late deliveries, low reviews, inactivity thresholds).

`train_churn()` writes `models/model.pkl`, `models/metrics.json`, `models/feature_importance.json`, `models/drift_reference.json`.

## Testing conventions

- `tests/conftest.py` builds a real (temp-file) SQLite mart from fixture CSVs in `tests/fixtures/` via the actual `build_mart()` — the `test_db_path` fixture is session-scoped since building it is the expensive part. Prefer testing through this real mart over mocking `SalesMart`.
- `churn_mart` fixture hand-constructs a minimal `fact_orders` table with known seller timelines around a fixed cutoff, specifically to exercise churn labeling/feature edge cases without depending on the full ETL.
- Leakage boundaries (features/labels never crossing the cutoff) are the main invariant worth testing when touching `src/churn/`.

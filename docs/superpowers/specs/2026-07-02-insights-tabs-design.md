# Insights Tabs — Remove LLM Chat, Add Analytics Tabs

**Date:** 2026-07-02
**Status:** Approved

## Goal

Remove the NVIDIA NIM chat ("Questions" tab) entirely and replace it with four
new analytics tabs built from data the app already loads, plus the trained
churn model artifacts. The app stops requiring an API key.

## Out of Scope

- No changes to ETL (`src/etl.py`, `sql/`), `src/mart.py`, `src/churn/` logic,
  or the Segmentación tab.
- No new mart tables or views.

## Removal

| Item | Action |
|------|--------|
| `src/agent.py` | Delete file |
| `app.py` chat block (tab2), `get_agent`, NVAPI check, `load_dotenv` | Delete |
| `tests/` referencing the agent (if any) | Delete |
| `langchain`, `langchain-experimental`, `langchain-nvidia-ai-endpoints`, `langchain-groq`, `groq`, `tabulate`, `python-dotenv` | Remove from `Pipfile` and `requirements.txt` |

`tabulate` existed only for the agent's `df.to_markdown()`; `python-dotenv`
existed only to load the NVAPI key. Both go.

## New Tab Structure

Six tabs total:

```
📊 Analysis | 🚚 Logística | ⭐ Reviews | 📉 Churn Sellers | 💰 Ventas | 🧩 Segmentación
```

## Architecture

Approach A (approved): pure chart-builder functions in `src/charts.py`,
per-block aggregation functions in `src/analysis.py`, `app.py` only wires
tabs. Same pattern the app already uses; everything testable without
Streamlit.

### `src/analysis.py` — new pure functions (DataFrame in, DataFrame out)

- `delay_distribution(df)` — delivery delay histogram input (clipped to a
  sane display range, e.g. [-30, 60] days).
- `late_rate_by_state(df)` — % of orders with `delivery_delay_days > 0` per
  `customer_state`.
- `distance_delay_sample(df, n=5000, seed=42)` — deterministic sample for the
  scatter so Plotly stays responsive.
- `review_distribution(df)` — order counts per `review_score` (1–5).
- `delay_by_review_score(df)` — average delay per review score.
- `monthly_aov(df)` — average order value per month.
- `freight_share_by_category(df, top=10)` — freight as % of payment value for
  the top-N categories by revenue.

### `src/charts.py` — new figure builders

- `histogram_chart(df, x, title)` — generic histogram.
- `scatter_chart(df, x, y, title)` — generic scatter.
- `feature_importance_chart(importance: dict) -> Figure` — horizontal bars,
  sorted. **Signature fixed by the pre-existing failing test**
  `tests/test_charts.py::test_feature_importance_chart`.
- `confusion_matrix_chart(matrix: list[list]) -> Figure` — 2×2 heatmap via
  `px.imshow`. **Signature fixed by**
  `tests/test_charts.py::test_confusion_matrix_chart`.
- Existing `bar_chart`/`line_chart` reused for the rest.

### Churn Sellers tab

Reads trained artifacts from `models/`:

- `models/feature_importance.json` → `feature_importance_chart`
- `models/metrics.json` → KPI metrics row (AUC etc.) and, if the saved
  metrics include a confusion matrix, `confusion_matrix_chart`
- `ChurnScorer` (existing `src/churn/predict.py`) → top-20 at-risk sellers
  table with recommendations, computed at `cutoff = max_order_date` so it
  scores current sellers.

Guard: if `models/model.pkl` is missing, the tab shows
`st.warning` with the command `python -m src.churn.train` and renders nothing
else — same pattern as the existing mart-existence check. The model is
trained once as part of this change so the tab is demonstrable; `models/` is
not committed.

Scoring is wrapped in `@st.cache_data`/`@st.cache_resource` like the other
loaders.

## Error Handling

- Churn tab: missing `models/` → warning, no crash.
- All other tabs consume the already-loaded `df`; no new failure modes.

## Testing

- Delete agent tests if any exist.
- `tests/test_charts.py`: the two currently-failing tests
  (`feature_importance_chart`, `confusion_matrix_chart`) pass once the
  functions exist. Add smoke tests (returns `Figure`) for the new chart
  builders.
- `tests/test_analysis.py` (or extend existing analysis tests): unit tests
  for each new aggregation function against `sample_df`-style fixtures —
  known input, asserted output values.
- Full suite must end 100% green (no pre-existing failures remain).

## Success Criteria

1. App runs with no `NVAPI` env var and no langchain installed.
2. Six tabs render; Churn tab degrades gracefully without `models/`.
3. `pytest tests/ -v` fully green.

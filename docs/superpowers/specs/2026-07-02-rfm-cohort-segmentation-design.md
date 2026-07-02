# RFM + Cohort Retention Segmentation — Design

## Goal

Add a customer segmentation capability (RFM classic scoring + monthly cohort
retention) to the Sales Assistant app, following the X/Y/Z framing: for each
KPI surfaced, state what was achieved, how it's measured, and how it was
computed — not just render a chart.

## Background / Verified Facts

- Olist's `customer_id` is scoped to a single order, not a person.
  `customer_unique_id` (present in `raw_customers`, absent from
  `stg_customers`/`dim_customers` today) is the correct grain for RFM
  Frequency and cohort retention.
- Verified against the raw CSVs: 96,096 unique customers
  (`customer_unique_id`), only 2,997 (3.12%) place more than one order.
  This means most RFM segments will skew toward single-purchase behavior,
  and cohort retention will be low across the board — this is a real
  property of the dataset, not a bug, and must be called out in the UI
  copy so it doesn't read as broken.

## Scope

### 1. ETL changes (schema, following existing raw → stg → mart → quality → views sequence)

- `sql/clean.sql`: `stg_customers` gains `customer_unique_id` (carried
  straight from `raw_customers`).
- `sql/mart.sql`: `dim_customers` gains `customer_unique_id`. `fact_orders`
  is unchanged — it keeps joining on `customer_id`; consumers resolve
  person-level identity via `dim_customers`.
- `sql/quality.sql`: new check block, `-- CHECK: customer_unique_id not null`,
  same pattern as existing checks (must return zero rows).
- `docs/data-dictionary.md`: document the `customer_id` (grain: order) vs
  `customer_unique_id` (grain: person) distinction.

This pattern (resolve a stable business-entity ID separately from a
raw per-event ID) is meant to be copy-pasteable into future projects with
the same shape (sessions vs. user, tickets vs. customer, etc).

### 2. `src/segmentation.py` (new module, same standalone-package pattern as `src/churn/`)

- `RFMBuilder`: reads `fact_orders` + `dim_customers` via `SalesMart`,
  computes Recency/Frequency/Monetary per `customer_unique_id`, assigns
  quintile scores (1-5) per dimension, maps score combinations to named
  segments (Champions, Loyal, At Risk, Hibernating, etc.) via a fixed
  rules table — classic RFM, no clustering.
- `CohortBuilder`: groups customers by month of first purchase
  (`customer_unique_id`), builds a monthly retention matrix. Retention
  window (6 or 12 months) is a parameter, not two separate functions.
  Cohorts younger than the requested window are marked as `null` (not 0%)
  for the not-yet-elapsed months — a cohort that hasn't had 6 months to
  return should not display as "0% retained".
- `compute_kpis()`: returns a dict with:
  - Retention at M1, M3, M6, M12 (point-in-time, not cumulative)
  - Global repeat-purchase rate
  - Best/worst cohort by M3 retention
  - Segment size (count) and % of total revenue per RFM segment
  - Highest-risk segment (At Risk / Hibernating) with its historical revenue

### 3. UI — `app.py`

New "Segmentación" tab, cached the same way as `load_data`
(`st.cache_data` on the builder calls). Layout: KPI cards (`st.metric`) at
top, cohort retention heatmap (Plotly) with a 6/12-month toggle, RFM
segment table below. Caption noting the low baseline repeat-purchase rate
so the retention numbers are read in context.

## Error Handling / Edge Cases

- Cohorts too recent to have reached a given month offset: represented as
  `null`/gray in the heatmap, never as `0%`.
- Customers with Frequency=1 (the ~97% majority): expected to cluster in
  low F-score segments — this is correct behavior, documented in a UI
  caption, not treated as a defect.

## Testing (deferred to end of project, per prior agreement)

Focus areas when tests are eventually written:
- Quintile scoring correctness against the real skewed distribution
  (heavy concentration at Frequency=1).
- Cohort math: cohorts without enough elapsed time do not report 0%.
- `customer_unique_id` correctly collapses repeat `customer_id`s to the
  same person.

## Out of Scope

- KMeans/clustering-based segmentation (considered, rejected in favor of
  classic RFM given the single-purchase-dominant distribution).
- Any change to `fact_orders` schema.

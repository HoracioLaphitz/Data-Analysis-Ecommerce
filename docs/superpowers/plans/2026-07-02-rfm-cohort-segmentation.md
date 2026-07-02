# RFM + Cohort Retention Segmentation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a "Segmentación" capability to the app — classic RFM scoring and monthly cohort retention — backed by a corrected `customer_unique_id` grain in the mart, surfaced as business KPIs (not just charts).

**Architecture:** Extend the ETL (`clean.sql`/`mart.sql`/`quality.sql`) to carry `customer_unique_id` through to `dim_customers`. Add one new standalone module `src/segmentation.py` (same pattern as `src/churn/`) with `RFMBuilder`, `CohortBuilder`, and `compute_kpis()`. Add one new `SalesMart` read method and one new `charts.py` helper. Wire it into a new Streamlit tab in `app.py`.

**Tech Stack:** pandas, SQLite (existing mart), Plotly (`px.imshow` for the cohort heatmap), Streamlit.

## Global Constraints

- `customer_id` is order-scoped in this dataset; `customer_unique_id` is the person-scoped grain. All RFM/cohort logic MUST group by `customer_unique_id`, never `customer_id`.
- Verified fact: only 3.12% of customers (2,997 of 96,096) place more than one order. Any UI showing retention/frequency numbers MUST include a caption stating this baseline so low numbers don't read as a bug.
- `SalesMart` remains the only runtime SQL boundary — no raw `sqlite3` calls outside `src/mart.py`/`src/etl.py`.
- Testing is deferred to the final task per prior agreement — earlier tasks implement without a TDD test-first cycle, verified instead by a manual sanity-check step. The final task adds the full test suite.
- Follow existing code style: no type hints beyond what's already used in `src/churn/features.py` and `src/analysis.py` (plain function/class bodies, docstring on the class only).

---

### Task 1: Carry `customer_unique_id` through the ETL

**Files:**
- Modify: `sql/clean.sql:12-21` (`stg_customers`)
- Modify: `sql/mart.sql:3-5` (`dim_customers`)
- Modify: `sql/quality.sql` (append new check)
- Modify: `docs/data-dictionary.md:20-26` (`dim_customers` section)

**Interfaces:**
- Produces: `dim_customers.customer_unique_id` (TEXT, not null) — consumed by Task 2 (`SalesMart.customer_orders`).

- [ ] **Step 1: Update `stg_customers` to carry `customer_unique_id`**

In `sql/clean.sql`, replace the `stg_customers` block (lines 12-21):

```sql
-- Customers: normalize city, attach centroid.
DROP TABLE IF EXISTS stg_customers;
CREATE TABLE stg_customers AS
SELECT c.customer_id,
       c.customer_unique_id,
       c.customer_state,
       LOWER(TRIM(c.customer_city)) AS customer_city,
       g.lat, g.lng
FROM raw_customers c
LEFT JOIN stg_geolocation g ON c.customer_zip_code_prefix = g.zip
WHERE c.customer_id IS NOT NULL;
```

- [ ] **Step 2: Update `dim_customers` to carry `customer_unique_id`**

In `sql/mart.sql`, replace lines 3-5:

```sql
DROP TABLE IF EXISTS dim_customers;
CREATE TABLE dim_customers AS
SELECT customer_id, customer_unique_id, customer_state, customer_city, lat, lng
FROM stg_customers;
```

- [ ] **Step 3: Add a quality check for the new column**

Append to `sql/quality.sql`:

```sql
-- CHECK: dim_customers_customer_unique_id_not_null
SELECT customer_id FROM dim_customers WHERE customer_unique_id IS NULL;
```

Note: the check name deliberately repeats `customer_unique_id` in full (not abbreviated) — Task 8's quality test asserts the raised error message contains that exact substring.

- [ ] **Step 4: Document the grain distinction**

In `docs/data-dictionary.md`, replace the `dim_sellers / dim_customers` section (lines 20-26):

```markdown
## dim_sellers
| column | type | cleaning |
|--------|------|----------|
| seller_id | TEXT | PK, not null, unique |
| seller_state | TEXT | — |
| seller_city | TEXT | LOWER(TRIM()) |
| lat, lng | REAL | ZIP centroid (mean) |

## dim_customers
| column | type | cleaning |
|--------|------|----------|
| customer_id | TEXT | PK, not null, unique — grain: one row per **order** |
| customer_unique_id | TEXT | not null — grain: one row per **person**. Olist issues a new `customer_id` per order, so `customer_id` alone cannot detect repeat customers. Always group by `customer_unique_id` for RFM/cohort/retention analysis. |
| customer_state | TEXT | — |
| customer_city | TEXT | LOWER(TRIM()) |
| lat, lng | REAL | ZIP centroid (mean) |
```

- [ ] **Step 5: Rebuild the mart and sanity-check manually**

Run:
```bash
python -m src.etl
python -c "
from src.mart import SalesMart
import sqlite3
conn = sqlite3.connect('data/olist_mart.db')
n_unique = conn.execute('SELECT COUNT(DISTINCT customer_unique_id) FROM dim_customers').fetchone()[0]
print('distinct customer_unique_id:', n_unique)
"
```
Expected: no `DataQualityError` raised during `python -m src.etl`, and the printed count is close to 96,096 (full dataset) — confirms the column populated correctly and the quality gate passed.

- [ ] **Step 6: Commit**

```bash
git add sql/clean.sql sql/mart.sql sql/quality.sql docs/data-dictionary.md
git commit -m "feat(etl): carry customer_unique_id into dim_customers"
```

---

### Task 2: Add `SalesMart.customer_orders()`

**Files:**
- Modify: `src/mart.py` (add method after `orders()`, i.e. after line 36)

**Interfaces:**
- Consumes: `dim_customers.customer_unique_id` from Task 1.
- Produces: `SalesMart.customer_orders() -> pd.DataFrame` with columns `order_id`, `customer_unique_id`, `order_purchase_timestamp` (parsed as datetime), `payment_value` — consumed by Task 3 (`RFMBuilder`) and Task 4 (`CohortBuilder`).

- [ ] **Step 1: Add the method**

In `src/mart.py`, insert after the `orders()` method (after line 36):

```python
    def customer_orders(self) -> pd.DataFrame:
        return self._read(
            """
            SELECT f.order_id, c.customer_unique_id,
                   f.order_purchase_timestamp, f.payment_value
            FROM fact_orders f
            JOIN dim_customers c ON f.customer_id = c.customer_id
            """,
            parse_dates=["order_purchase_timestamp"],
        )
```

- [ ] **Step 2: Sanity-check manually**

Run:
```bash
python -c "
from src.mart import SalesMart
mart = SalesMart('data/olist_mart.db')
df = mart.customer_orders()
print(df.shape)
print(df.dtypes)
print((df.groupby('customer_unique_id').size() > 1).mean())
"
```
Expected: shape has 4 columns; `order_purchase_timestamp` dtype is `datetime64[ns]`; the printed repeat-rate fraction is close to `0.0312` (3.12%), matching the verified fact from the design doc.

- [ ] **Step 3: Commit**

```bash
git add src/mart.py
git commit -m "feat(mart): add customer_orders read method"
```

---

### Task 3: `RFMBuilder`

**Files:**
- Create: `src/segmentation.py`

**Interfaces:**
- Consumes: `SalesMart.customer_orders()` (Task 2).
- Produces: `RFMBuilder().build(mart, reference_date=None) -> pd.DataFrame`, indexed by `customer_unique_id`, columns `recency_days` (float), `frequency` (float), `monetary` (float), `R` (int 1-5), `F` (int 1-5), `M` (int 1-5), `segment` (str). Consumed by Task 5 (`compute_kpis`) and Task 7 (`app.py`).

- [ ] **Step 1: Create the file with `RFMBuilder`**

```python
import pandas as pd


class RFMBuilder:
    """Classic RFM scoring per customer_unique_id (not customer_id — see
    docs/data-dictionary.md for why customer_id can't detect repeat buyers)."""

    def build(self, mart, reference_date: pd.Timestamp | None = None) -> pd.DataFrame:
        orders = mart.customer_orders()
        if reference_date is None:
            reference_date = orders["order_purchase_timestamp"].max()

        g = orders.groupby("customer_unique_id")
        rfm = pd.DataFrame({
            "recency_days": (reference_date - g["order_purchase_timestamp"].max()).dt.days.astype(float),
            "frequency": g["order_id"].nunique().astype(float),
            "monetary": g["payment_value"].sum(),
        })

        # rank(method="first") breaks ties before qcut so equal recency/monetary
        # values don't collide into a single bin edge.
        rfm["R"] = pd.qcut(rfm["recency_days"].rank(method="first"), 5, labels=[5, 4, 3, 2, 1]).astype(int)
        # Frequency is NOT quintile-scored: ~97% of Olist customers place a
        # single order (verified against raw data), so a quantile split would
        # assign arbitrary, meaningless different scores to identical behavior.
        # Cap the raw order count instead — 1 order = score 1, 5+ orders = score 5.
        rfm["F"] = rfm["frequency"].clip(upper=5).astype(int)
        rfm["M"] = pd.qcut(rfm["monetary"].rank(method="first"), 5, labels=[1, 2, 3, 4, 5]).astype(int)

        rfm["segment"] = rfm.apply(self._segment, axis=1)
        return rfm

    @staticmethod
    def _segment(row) -> str:
        r, f = row["R"], row["F"]
        if r >= 4 and f >= 4:
            return "Champions"
        if r >= 3 and f >= 4:
            return "Loyal"
        if r >= 4 and f <= 3:
            return "New Customers"
        if r <= 2 and f >= 3:
            return "At Risk"
        if r <= 2 and f <= 2:
            return "Hibernating"
        return "Need Attention"
```

- [ ] **Step 2: Sanity-check manually**

Run:
```bash
python -c "
from src.mart import SalesMart
from src.segmentation import RFMBuilder
mart = SalesMart('data/olist_mart.db')
rfm = RFMBuilder().build(mart)
print(rfm['segment'].value_counts())
print(rfm[['R','F','M']].describe())
"
```
Expected: segment counts sum to ~96,096; `F` column is overwhelmingly `1` (matches the 3.12% repeat rate); no exception raised (confirms the qcut tie-breaking works on real skewed data).

- [ ] **Step 3: Commit**

```bash
git add src/segmentation.py
git commit -m "feat(segmentation): add RFMBuilder"
```

---

### Task 4: `CohortBuilder`

**Files:**
- Modify: `src/segmentation.py` (append class)

**Interfaces:**
- Consumes: `SalesMart.customer_orders()` (Task 2).
- Produces: `CohortBuilder().build(mart, window_months=12) -> pd.DataFrame`, a pivot table indexed by `cohort_month` (`pandas.Period[M]`), columns `0..window_months` (int month offsets), values = retention percentage (float) or `None`/`NaN` for cohorts that haven't reached that offset yet. Consumed by Task 5 (`compute_kpis`) and Task 7 (`app.py`).

- [ ] **Step 1: Append `CohortBuilder` to `src/segmentation.py`**

```python
class CohortBuilder:
    """Monthly cohort retention matrix, keyed by month of first purchase
    (customer_unique_id grain)."""

    def build(self, mart, window_months: int = 12) -> pd.DataFrame:
        orders = mart.customer_orders()
        orders = orders.assign(
            order_month=orders["order_purchase_timestamp"].dt.to_period("M")
        )
        first_month = orders.groupby("customer_unique_id")["order_month"].min()
        orders = orders.join(first_month.rename("cohort_month"), on="customer_unique_id")
        orders["month_offset"] = (orders["order_month"] - orders["cohort_month"]).apply(lambda p: p.n)
        orders = orders[orders["month_offset"].between(0, window_months)]

        cohort_sizes = (
            orders[orders["month_offset"] == 0]
            .groupby("cohort_month")["customer_unique_id"].nunique()
        )

        active = (
            orders.groupby(["cohort_month", "month_offset"])["customer_unique_id"]
            .nunique()
            .reset_index(name="active_customers")
        )
        active["cohort_size"] = active["cohort_month"].map(cohort_sizes)
        active["retention_pct"] = active["active_customers"] / active["cohort_size"] * 100

        matrix = active.pivot(index="cohort_month", columns="month_offset", values="retention_pct")

        # A cohort that hasn't had enough elapsed time to reach a given month
        # offset must show as "no data yet" (NaN), never as "0% retained" —
        # otherwise recent cohorts look like total churn when they simply
        # haven't had the chance to return yet.
        max_month = orders["order_month"].max()
        for cohort_month in matrix.index:
            for offset in matrix.columns:
                if cohort_month + offset > max_month:
                    matrix.loc[cohort_month, offset] = float("nan")
        return matrix
```

- [ ] **Step 2: Sanity-check manually**

Run:
```bash
python -c "
from src.mart import SalesMart
from src.segmentation import CohortBuilder
mart = SalesMart('data/olist_mart.db')
m = CohortBuilder().build(mart, window_months=12)
print(m.shape)
print(m.iloc[-1])  # most recent cohort: later offsets should be NaN
"
```
Expected: the most recent cohort row shows real percentages for early offsets and `NaN` for offsets it hasn't reached yet (not `0.0`).

- [ ] **Step 3: Commit**

```bash
git add src/segmentation.py
git commit -m "feat(segmentation): add CohortBuilder"
```

---

### Task 5: `compute_kpis()`

**Files:**
- Modify: `src/segmentation.py` (append function)

**Interfaces:**
- Consumes: `RFMBuilder().build()` (Task 3), `CohortBuilder().build()` (Task 4).
- Produces: `compute_kpis(mart, window_months=12) -> dict` with keys `segment_sizes` (dict[str,int]), `revenue_pct_by_segment` (dict[str,float]), `global_repeat_rate` (float), `risk_segment_revenue` (float), `retention` (dict with keys `"M1"`,`"M3"`,`"M6"`,`"M12"`, values float or `None`), `best_cohort_m3` (str or `None`), `worst_cohort_m3` (str or `None`). Consumed by Task 7 (`app.py`).

- [ ] **Step 1: Append `compute_kpis` to `src/segmentation.py`**

```python
def compute_kpis(mart, window_months: int = 12) -> dict:
    rfm = RFMBuilder().build(mart)
    cohorts = CohortBuilder().build(mart, window_months=window_months)

    total_monetary = rfm["monetary"].sum()
    revenue_pct_by_segment = (
        rfm.groupby("segment")["monetary"].sum() / total_monetary * 100
    ).round(1).to_dict()
    segment_sizes = rfm["segment"].value_counts().to_dict()

    risk_segments = ["At Risk", "Hibernating"]
    risk_revenue = rfm.loc[rfm["segment"].isin(risk_segments), "monetary"].sum()

    global_repeat_rate = round((rfm["frequency"] > 1).mean() * 100, 2)

    retention = {}
    for m in (1, 3, 6, 12):
        if m in cohorts.columns:
            value = cohorts[m].mean(skipna=True)
            retention[f"M{m}"] = round(value, 1) if pd.notna(value) else None
        else:
            retention[f"M{m}"] = None

    best_cohort = worst_cohort = None
    if 3 in cohorts.columns:
        m3 = cohorts[3].dropna()
        if not m3.empty:
            best_cohort = str(m3.idxmax())
            worst_cohort = str(m3.idxmin())

    return {
        "segment_sizes": segment_sizes,
        "revenue_pct_by_segment": revenue_pct_by_segment,
        "global_repeat_rate": global_repeat_rate,
        "risk_segment_revenue": round(risk_revenue, 2),
        "retention": retention,
        "best_cohort_m3": best_cohort,
        "worst_cohort_m3": worst_cohort,
    }
```

- [ ] **Step 2: Sanity-check manually**

Run:
```bash
python -c "
from src.mart import SalesMart
from src.segmentation import compute_kpis
mart = SalesMart('data/olist_mart.db')
import json
print(json.dumps(compute_kpis(mart), indent=2, default=str))
"
```
Expected: valid JSON printed, `global_repeat_rate` close to `3.12`, `retention` dict has 4 keys, no exception.

- [ ] **Step 3: Commit**

```bash
git add src/segmentation.py
git commit -m "feat(segmentation): add compute_kpis"
```

---

### Task 6: Cohort heatmap chart helper

**Files:**
- Modify: `src/charts.py` (append function)

**Interfaces:**
- Consumes: a `pd.DataFrame` matrix shaped like `CohortBuilder().build()` output (Task 4), with a string index (caller converts `Period` index to string before calling).
- Produces: `heatmap_chart(matrix: pd.DataFrame, title: str) -> Figure` — consumed by Task 7 (`app.py`).

- [ ] **Step 1: Append `heatmap_chart` to `src/charts.py`**

```python
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
```

- [ ] **Step 2: Sanity-check manually**

Run:
```bash
python -c "
from src.mart import SalesMart
from src.segmentation import CohortBuilder
from src.charts import heatmap_chart
mart = SalesMart('data/olist_mart.db')
m = CohortBuilder().build(mart, window_months=12)
m.index = m.index.astype(str)
fig = heatmap_chart(m, 'test')
print(type(fig))
"
```
Expected: prints `<class 'plotly.graph_objs._figure.Figure'>`, no exception.

- [ ] **Step 3: Commit**

```bash
git add src/charts.py
git commit -m "feat(charts): add heatmap_chart helper"
```

---

### Task 7: "Segmentación" tab in `app.py`

**Files:**
- Modify: `app.py`

**Interfaces:**
- Consumes: `RFMBuilder`, `CohortBuilder`, `compute_kpis` (Tasks 3-5), `heatmap_chart` (Task 6), `SalesMart` (existing).

- [ ] **Step 1: Add imports**

In `app.py`, after line 6 (`from src.agent import build_agent, ask`):

```python
from src.mart import SalesMart
from src.segmentation import RFMBuilder, CohortBuilder, compute_kpis
from src.charts import heatmap_chart
```

- [ ] **Step 2: Add the cached segmentation loader**

After the existing `get_agent` cache function (after line 44), add:

```python
@st.cache_data
def get_segmentation(window_months):
    mart = SalesMart(DB_PATH)
    rfm = RFMBuilder().build(mart)
    cohorts = CohortBuilder().build(mart, window_months=window_months)
    kpis = compute_kpis(mart, window_months=window_months)
    return rfm, cohorts, kpis
```

- [ ] **Step 3: Add the third tab**

Replace line 60 (`tab1, tab2 = st.tabs(["📊 Analysis", "💬 Questions"])`) with:

```python
tab1, tab2, tab3 = st.tabs(["📊 Analysis", "💬 Questions", "🧩 Segmentación"])
```

Then, after the `with tab2:` block ends (after line 123), add:

```python

with tab3:
    window = st.radio(
        "Ventana de retención", [6, 12], index=1,
        horizontal=True, format_func=lambda m: f"{m} meses",
    )
    with st.spinner("Calculando segmentación..."):
        rfm, cohorts, kpis = get_segmentation(window)

    st.caption(
        "Solo 3.12% de los clientes de Olist repite compra — "
        "la retención y los segmentos reflejan ese comportamiento real, "
        "no un error de cálculo."
    )

    col1, col2, col3 = st.columns(3)
    col1.metric("Tasa de repetición global", f"{kpis['global_repeat_rate']}%")
    col2.metric("Revenue en riesgo (At Risk + Hibernating)", f"R$ {kpis['risk_segment_revenue']:,.0f}")
    m3_val = kpis["retention"].get("M3")
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
    segment_table["% Revenue"] = segment_table["Segmento"].map(kpis["revenue_pct_by_segment"])
    st.dataframe(segment_table, use_container_width=True)
```

- [ ] **Step 4: Manual smoke test**

Run:
```bash
streamlit run app.py
```
Expected: app loads without traceback, "🧩 Segmentación" tab appears, switching the 6/12-month radio re-renders the heatmap, KPI cards show non-crashing values (`global_repeat_rate` near 3.12%).

- [ ] **Step 5: Commit**

```bash
git add app.py
git commit -m "feat(app): add Segmentación tab"
```

---

### Task 8: Test suite (deferred — implemented last per prior agreement)

**Files:**
- Create: `tests/test_segmentation.py`
- Modify: `tests/conftest.py` (add `segmentation_mart` fixture)
- Modify: `tests/test_etl_mart.py` (add one assertion)
- Modify: `tests/test_etl_quality.py` (check the file first — see Step 1)

**Interfaces:**
- Consumes: `RFMBuilder`, `CohortBuilder`, `compute_kpis` (Tasks 3-5), `SalesMart` (Task 2), `test_db_path` fixture (existing, `tests/conftest.py:34-43`).

- [ ] **Step 1: (context only, no action)** `tests/test_etl_quality.py` already exists and uses this pattern: copy `FIXTURES` to a temp dir, corrupt one CSV, assert `DataQualityError` is raised and mentions the broken field. Step 4 below follows that exact pattern.

- [ ] **Step 2: Add a hand-built fixture for cohort edge cases**

In `tests/conftest.py`, append (same pattern as the existing `churn_mart` fixture at lines 46-84):

```python
@pytest.fixture
def segmentation_mart(tmp_path):
    """SalesMart over a hand-built mart with controlled repeat-purchase and
    recency patterns, to exercise RFM scoring and cohort-masking edge cases.

    u1: two orders, Jan and Mar 2018 -> repeat customer, cohort=2018-01
    u2: one order, Jan 2018          -> single-purchase, cohort=2018-01
    u3: one order, Jul 2018 (the last month in this fixture) -> cohort=2018-07,
        too recent to have reached month_offset=3 -> must be NaN, not 0.
    """
    import sqlite3
    from src.mart import SalesMart
    db = str(tmp_path / "segmentation.db")
    conn = sqlite3.connect(db)
    conn.executescript(
        """
        CREATE TABLE fact_orders (
            order_id TEXT, customer_id TEXT, order_purchase_timestamp TEXT,
            payment_value REAL);
        CREATE TABLE dim_customers (
            customer_id TEXT, customer_unique_id TEXT);
        """
    )
    conn.executemany(
        "INSERT INTO fact_orders VALUES (?,?,?,?)",
        [
            ("o1", "c1", "2018-01-10 10:00:00", 100.0),
            ("o2", "c1b", "2018-03-15 10:00:00", 50.0),
            ("o3", "c2", "2018-01-20 10:00:00", 200.0),
            ("o4", "c3", "2018-07-05 10:00:00", 80.0),
        ],
    )
    conn.executemany(
        "INSERT INTO dim_customers VALUES (?,?)",
        [("c1", "u1"), ("c1b", "u1"), ("c2", "u2"), ("c3", "u3")],
    )
    conn.commit()
    conn.close()
    return SalesMart(db)
```

- [ ] **Step 3: Write `tests/test_segmentation.py`**

```python
import pandas as pd
import pytest
from src.segmentation import RFMBuilder, CohortBuilder, compute_kpis


def test_rfm_groups_by_customer_unique_id_not_customer_id(segmentation_mart):
    rfm = RFMBuilder().build(segmentation_mart)
    assert set(rfm.index) == {"u1", "u2", "u3"}
    assert rfm.loc["u1", "frequency"] == 2  # c1 + c1b both map to u1


def test_rfm_frequency_score_is_capped_not_quantile(segmentation_mart):
    rfm = RFMBuilder().build(segmentation_mart)
    assert rfm.loc["u1", "F"] == 2  # frequency clipped, not quantile-derived
    assert rfm.loc["u2", "F"] == 1
    assert rfm.loc["u3", "F"] == 1


def test_cohort_recent_cohort_is_nan_not_zero(segmentation_mart):
    matrix = CohortBuilder().build(segmentation_mart, window_months=12)
    u3_cohort = pd.Period("2018-07", freq="M")
    # u3's cohort is the last month in the fixture: month_offset=3 hasn't
    # happened yet and must be NaN, never 0.0.
    assert pd.isna(matrix.loc[u3_cohort, 3])


def test_cohort_month_zero_is_full_cohort(segmentation_mart):
    matrix = CohortBuilder().build(segmentation_mart, window_months=12)
    jan_cohort = pd.Period("2018-01", freq="M")
    assert matrix.loc[jan_cohort, 0] == 100.0


def test_cohort_month_two_shows_repeat_customer_only(segmentation_mart):
    matrix = CohortBuilder().build(segmentation_mart, window_months=12)
    jan_cohort = pd.Period("2018-01", freq="M")
    # Jan cohort has u1 and u2; only u1 returns in month offset 2 (March).
    assert matrix.loc[jan_cohort, 2] == 50.0


def test_compute_kpis_shape(segmentation_mart):
    kpis = compute_kpis(segmentation_mart, window_months=12)
    assert set(kpis["retention"].keys()) == {"M1", "M3", "M6", "M12"}
    assert kpis["global_repeat_rate"] == pytest.approx(100 / 3, abs=0.1)


def test_rfm_on_real_mart_matches_verified_repeat_rate(test_db_path):
    from src.mart import SalesMart
    mart = SalesMart(test_db_path)
    rfm = RFMBuilder().build(mart)
    # Fixture dataset is small; this just confirms the pipeline runs
    # end-to-end against the real ETL output without raising.
    assert not rfm.empty
    assert "segment" in rfm.columns
```

- [ ] **Step 4: Add a quality-check test for `customer_unique_id`**

Append to `tests/test_etl_quality.py`:

```python
def test_null_customer_unique_id_raises(tmp_path):
    from src.etl import build_mart
    from src.errors import DataQualityError
    dirty = tmp_path / "dirty"
    shutil.copytree(FIXTURES, dirty)
    # inject a row with a blank customer_unique_id (parses as NULL)
    customers = dirty / "olist_customers_dataset.csv"
    with open(customers, "a", encoding="utf-8") as f:
        f.write("c99,,01000,sao paulo,SP\n")
    with pytest.raises(DataQualityError) as exc:
        build_mart(data_dir=str(dirty), db_path=str(tmp_path / "d.db"))
    assert "customer_unique_id" in str(exc.value).lower()
```

- [ ] **Step 5: Add one assertion to `tests/test_etl_mart.py`**

In `tests/test_etl_mart.py`, add a new test function:

```python
def test_dim_customers_has_unique_id(tmp_db):
    from src.etl import build_mart
    build_mart(data_dir=FIXTURES, db_path=tmp_db)
    conn = sqlite3.connect(tmp_db)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(dim_customers)").fetchall()}
    conn.close()
    assert "customer_unique_id" in cols
```

- [ ] **Step 6: Run the full test suite**

Run: `pytest tests/ -v`
Expected: all tests pass, including the new ones in `test_segmentation.py`, `test_etl_mart.py`, and `test_etl_quality.py`.

- [ ] **Step 7: Commit**

```bash
git add tests/test_segmentation.py tests/conftest.py tests/test_etl_mart.py tests/test_etl_quality.py
git commit -m "test(segmentation): add RFM/cohort test suite"
```

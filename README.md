# AI Sales Assistant

Analytics de e-commerce sobre 100k+ órdenes de Brasil (dataset Olist), con seis tabs de
insights en Streamlit y un pipeline de churn prediction para vendedores.

## Tabs de la app

- 📊 **Analysis** — KPIs generales (revenue, órdenes, AOV, distancia, demoras) y tendencias mensuales.
- 🚚 **Logística** — distribución de demoras de entrega, tasa de entregas tardías por estado y distancia vs. demora.
- ⭐ **Reviews** — distribución de review scores y su relación con la demora de entrega.
- 📉 **Churn Sellers** — métricas del modelo de churn (AUC-ROC, recall), feature importance y ranking de vendedores en riesgo con recomendaciones.
- 💰 **Ventas** — ticket promedio mensual (AOV) y peso del flete por categoría.
- 🧩 **Segmentación** — RFM, cohortes de retención mensual y KPIs de riesgo de revenue.

## Setup local

### 1. Descargar datos

Descargá el dataset de Kaggle:
https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce

 `data/`:
- `olist_orders_dataset.csv`
- `olist_order_items_dataset.csv`
- `olist_products_dataset.csv`
- `product_category_name_translation.csv`
- `olist_order_payments_dataset.csv`
- `olist_customers_dataset.csv`

### 2. Instalar dependencias

```bash
pip install -r requirements.txt
```

Para correr los tests también necesitás las dependencias de desarrollo:

```bash
pip install -r requirements-dev.txt
```

### 3. Build the Data Mart (once)

Download the [Olist dataset from Kaggle](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce)
and place all CSV files in the `data/` directory, then run:

```bash
python -m src.etl
```

This creates `data/olist_mart.db` (Star Schema SQLite). Run this once — the app reads only from the DB.
La app no funciona sin este archivo (no está en el repo, junto con los CSV crudos).

### 4. (Opcional) Entrenar el modelo de churn

Para habilitar la tab de Churn Sellers:

```bash
python -m src.churn.train
```

Esto genera los artifacts en `models/` (`model.pkl`, `metrics.json`, `feature_importance.json`,
`drift_reference.json`). Si no existen, la tab muestra una advertencia y no rompe la app.

### 5. Correr la app

```bash
streamlit run app.py
```

## Tests

```bash
pytest tests/ -v
```


## Stack

- Streamlit
- Plotly Express
- Pandas
- Scikit-learn + XGBoost (churn prediction)
- Dataset: Brazilian E-Commerce Public Dataset (Olist) via Kaggle

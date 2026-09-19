# Analytics de e-commerce

Proyecto desarrollado sobre 100k+ órdenes de Brasil (dataset Olist), con seis tabs de
insights en Streamlit y un pipeline de churn prediction para vendedores.

## Tabs de la app

- 📊 **Analysis** — KPIs generales (revenue, órdenes, AOV, distancia, demoras) y tendencias mensuales.
- 🚚 **Logística** — distribución de demoras de entrega, tasa de entregas tardías por estado y distancia vs. demora.
- ⭐ **Reviews** — distribución de review scores y su relación con la demora de entrega.
- 📉 **Churn Sellers** — métricas del modelo de churn (AUC-ROC, recall), feature importance y ranking de vendedores en riesgo con recomendaciones.
- 💰 **Ventas** — ticket promedio mensual (AOV) y peso del flete por categoría.
- 🧩 **Segmentación** — RFM, cohortes de retención mensual y KPIs de riesgo de revenue.

### Dataset

https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce

 `data/`:
- `olist_orders_dataset.csv`
- `olist_order_items_dataset.csv`
- `olist_products_dataset.csv`
- `product_category_name_translation.csv`
- `olist_order_payments_dataset.csv`
- `olist_customers_dataset.csv`

## Stack

- Streamlit
- Plotly Express
- Pandas
- Scikit-learn + XGBoost (churn prediction)
- Dataset: Brazilian E-Commerce Public Dataset (Olist) via Kaggle

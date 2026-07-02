# AI Sales Assistant

Chat en lenguaje natural sobre 100k+ órdenes de e-commerce de Brasil.
Analizá datos de Olist con LangChain + NVIDIA NIM llama3-70b desde una interfaz Streamlit.

## Setup local

### 1. Descargar datos

Descargá el dataset de Kaggle:
https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce

Copiá estos archivos en `data/`:
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

### 3. Build the Data Mart (once)

Download the [Olist dataset from Kaggle](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce)
and place all CSV files in the `data/` directory, then run:

```bash
python -m src.etl
```

This creates `data/olist_mart.db` (Star Schema SQLite). Run this once — the app reads only from the DB.

### 4. Configurar API key

Obtené tu NVIDIA NIM API key gratuita en https://build.nvidia.com/

```bash
# Windows PowerShell
$env:NVAPI="tu_api_key_aqui"

# macOS / Linux
export NVAPI="tu_api_key_aqui"
```

### 5. Correr la app

```bash
streamlit run app.py
```

## Tests

```bash
pytest tests/ -v
```

## Deploy en Streamlit Cloud

1. Fork este repo
2. Ir a https://streamlit.io/cloud → New app → seleccionar este repo
3. Main file: `Proyectos/ai-sales-assistant/app.py`
4. Secrets: `NVAPI = "tu_key"`

## Stack

- LangChain + langchain-experimental (Pandas DataFrame Agent)
- NVIDIA NIM llama3-70b
- Streamlit
- Plotly Express
- Pandas
- Dataset: Brazilian E-Commerce Public Dataset (Olist) via Kaggle

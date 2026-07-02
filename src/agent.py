from typing import Any

import pandas as pd
from langchain_nvidia_ai_endpoints import ChatNVIDIA

try:
    from langchain_experimental.agents import create_pandas_dataframe_agent
except Exception:  # pragma: no cover — binary compat guard for CI/test envs
    create_pandas_dataframe_agent = None  # type: ignore[assignment]

MODEL = "meta/llama-3.3-70b-instruct"

SYSTEM_PREFIX = """Sos un asistente de análisis de ventas para datos de e-commerce de Brasil.
Respondés en español con números concretos y contexto de negocio.
Cuando el resultado sea una tabla o serie de datos, describila en lenguaje natural.
Si la pregunta no está relacionada con los datos de ventas, indicalo amablemente."""


def build_agent(df: pd.DataFrame, api_key: str) -> Any:
    if create_pandas_dataframe_agent is None:
        raise ImportError(
            "langchain_experimental unavailable. Run: pip install langchain-experimental"
        )
    llm = ChatNVIDIA(model=MODEL, api_key=api_key, temperature=0)
    agent = create_pandas_dataframe_agent(
        llm,
        df,
        verbose=True,
        allow_dangerous_code=True,
        prefix=SYSTEM_PREFIX,
        agent_executor_kwargs={"handle_parsing_errors": True},
    )
    return agent


def ask(agent: Any, question: str) -> dict:
    try:
        result = agent.invoke({"input": question})
        return {
            "answer": result.get("output", "Sin respuesta."),
            "intermediate_steps": result.get("intermediate_steps", []),
        }
    except Exception as e:
        return {
            "answer": f"No pude procesar la pregunta. Error: {str(e)}",
            "intermediate_steps": [],
        }

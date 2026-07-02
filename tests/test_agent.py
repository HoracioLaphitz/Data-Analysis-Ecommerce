import pytest
from unittest.mock import MagicMock, patch
from src.agent import build_agent, ask


def test_build_agent_returns_executor(sample_df):
    with patch("src.agent.ChatNVIDIA") as mock_llm_cls, \
         patch("src.agent.create_pandas_dataframe_agent") as mock_create:
        mock_llm = MagicMock()
        mock_llm_cls.return_value = mock_llm
        mock_executor = MagicMock()
        mock_create.return_value = mock_executor

        agent = build_agent(sample_df, api_key="test-key")

        mock_llm_cls.assert_called_once_with(
            model="meta/llama-3.3-70b-instruct", api_key="test-key", temperature=0
        )
        mock_create.assert_called_once()
        assert agent is mock_executor


def test_ask_returns_dict_with_answer(sample_df):
    mock_agent = MagicMock()
    mock_agent.invoke.return_value = {
        "output": "El mes con más ventas fue enero con R$ 110.",
        "intermediate_steps": [("action", "observation")],
    }

    result = ask(mock_agent, "¿Cuál fue el mejor mes?")

    assert "answer" in result
    assert "intermediate_steps" in result
    assert result["answer"] == "El mes con más ventas fue enero con R$ 110."
    assert isinstance(result["intermediate_steps"], list)


def test_ask_handles_error_gracefully(sample_df):
    mock_agent = MagicMock()
    mock_agent.invoke.side_effect = Exception("API error")

    result = ask(mock_agent, "pregunta que falla")

    assert "answer" in result
    assert "error" in result["answer"].lower() or "no pude" in result["answer"].lower()

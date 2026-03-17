from __future__ import annotations

import asyncio
import os
from time import perf_counter
from typing import Any, TypeVar

from crewai import Crew, Process
from pydantic import BaseModel

from agents import DEFAULT_GROQ_MODEL, build_agents, build_groq_llm
from models import AnalyzeResponse, AttachmentSummary, FinalRecommendation, NewsDigest, TechnicalAnalysis
from tasks import build_strategist_task
from tools import DuckDuckGoNewsTool, YFinanceTechnicalsTool

ModelT = TypeVar("ModelT", bound=BaseModel)
ANALYSIS_TIMEOUT_SECONDS = 35


def _coerce_task_output(task_output: Any, model_cls: type[ModelT]) -> ModelT:
    pydantic_output = getattr(task_output, "pydantic", None)
    if pydantic_output is not None:
        return model_cls.model_validate(pydantic_output)

    raw_output = getattr(task_output, "raw", None) or getattr(task_output, "result", None)
    if raw_output:
        return model_cls.model_validate_json(raw_output)

    raise ValueError(f"Task output did not contain a valid {model_cls.__name__} payload.")


async def analyze_stock(
    ticker: str,
    model_name: str | None = None,
    attachments: list[AttachmentSummary] | None = None,
) -> AnalyzeResponse:
    normalized_ticker = ticker.strip().upper()
    start = perf_counter()

    technicals = TechnicalAnalysis.model_validate_json(YFinanceTechnicalsTool()._run(normalized_ticker))
    news = NewsDigest.model_validate_json(DuckDuckGoNewsTool()._run(normalized_ticker))

    llm = build_groq_llm(model_name)
    agents = build_agents(llm)
    strategist_task = build_strategist_task(agents, technicals, news)

    crew = Crew(
        agents=[agents.quantitative_strategist],
        tasks=[strategist_task],
        process=Process.sequential,
        verbose=False,
        memory=False,
        cache=True,
    )
    try:
        result = await asyncio.wait_for(
            asyncio.to_thread(crew.kickoff),
            timeout=ANALYSIS_TIMEOUT_SECONDS,
        )
    except TimeoutError as exc:
        raise TimeoutError(
            f"Analysis exceeded {ANALYSIS_TIMEOUT_SECONDS} seconds for ticker '{normalized_ticker}'."
        ) from exc
    latency_seconds = round(perf_counter() - start, 2)

    task_outputs = getattr(result, "tasks_output", None) or []
    if len(task_outputs) < 1:
        raise ValueError("CrewAI did not return a strategist output.")

    recommendation = _coerce_task_output(task_outputs[0], FinalRecommendation)

    return AnalyzeResponse(
        ticker=normalized_ticker,
        model=model_name or os.getenv("GROQ_MODEL", DEFAULT_GROQ_MODEL),
        latency_seconds=latency_seconds,
        attachments=attachments or [],
        technicals=technicals,
        news=news,
        recommendation=recommendation,
    )

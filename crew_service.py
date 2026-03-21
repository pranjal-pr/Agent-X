from __future__ import annotations

import asyncio
import os
from time import perf_counter
from typing import Any, TypeVar

from crewai import Crew, Process
from pydantic import BaseModel

from agents import DEFAULT_GROQ_MODEL, build_agents, build_groq_llm
from models import AnalyzeResponse, AttachmentSummary, FinalRecommendation, NewsDigest, TechnicalAnalysis
from tasks import build_tasks
from tools import resolve_stock_query

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


def _resolve_task_outputs(result: Any, tasks: list[Any]) -> list[Any]:
    task_outputs = list(getattr(result, "tasks_output", None) or [])
    if len(task_outputs) >= len(tasks):
        return task_outputs

    fallback_outputs = [getattr(task, "output", None) for task in tasks]
    if len(fallback_outputs) >= len(tasks) and all(output is not None for output in fallback_outputs):
        return fallback_outputs

    raise ValueError("CrewAI did not return all expected task outputs.")


async def analyze_stock(
    ticker: str,
    model_name: str | None = None,
    attachments: list[AttachmentSummary] | None = None,
) -> AnalyzeResponse:
    resolved_stock = await asyncio.to_thread(resolve_stock_query, ticker)
    normalized_ticker = resolved_stock.symbol
    start = perf_counter()

    llm = build_groq_llm(model_name)
    agents = build_agents(llm)
    tasks = build_tasks(agents, normalized_ticker, resolved_stock.company_name)

    crew = Crew(
        agents=agents.as_list(),
        tasks=tasks,
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

    task_outputs = _resolve_task_outputs(result, tasks)
    technicals = _coerce_task_output(task_outputs[0], TechnicalAnalysis)
    news = _coerce_task_output(task_outputs[1], NewsDigest)
    recommendation = _coerce_task_output(task_outputs[2], FinalRecommendation)

    if resolved_stock.company_name and not technicals.company_name:
        technicals = technicals.model_copy(update={"company_name": resolved_stock.company_name})

    return AnalyzeResponse(
        ticker=normalized_ticker,
        model=model_name or os.getenv("GROQ_MODEL", DEFAULT_GROQ_MODEL),
        latency_seconds=latency_seconds,
        attachments=attachments or [],
        technicals=technicals,
        news=news,
        recommendation=recommendation,
    )

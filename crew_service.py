from __future__ import annotations

import asyncio
import os
from time import perf_counter
from typing import Any, TypeVar

from crewai import Crew, Process
from pydantic import BaseModel

from agents import DEFAULT_GROQ_MODEL, build_agents, build_groq_llm
from models import AnalyzeResponse, FinalRecommendation, NewsDigest, TechnicalAnalysis
from tasks import build_tasks

ModelT = TypeVar("ModelT", bound=BaseModel)


def _coerce_task_output(task_output: Any, model_cls: type[ModelT]) -> ModelT:
    pydantic_output = getattr(task_output, "pydantic", None)
    if pydantic_output is not None:
        return model_cls.model_validate(pydantic_output)

    raw_output = getattr(task_output, "raw", None) or getattr(task_output, "result", None)
    if raw_output:
        return model_cls.model_validate_json(raw_output)

    raise ValueError(f"Task output did not contain a valid {model_cls.__name__} payload.")


async def analyze_stock(ticker: str, model_name: str | None = None) -> AnalyzeResponse:
    normalized_ticker = ticker.strip().upper()
    llm = build_groq_llm(model_name)
    agents = build_agents(llm)
    tasks = build_tasks(agents, normalized_ticker)

    start = perf_counter()
    crew = Crew(
        agents=agents.as_list(),
        tasks=tasks,
        process=Process.sequential,
        verbose=False,
        memory=False,
        cache=True,
    )
    result = await asyncio.to_thread(crew.kickoff, inputs={"ticker": normalized_ticker})
    latency_seconds = round(perf_counter() - start, 2)

    task_outputs = getattr(result, "tasks_output", None) or []
    if len(task_outputs) < 3:
        raise ValueError("CrewAI did not return all task outputs.")

    technicals = _coerce_task_output(task_outputs[0], TechnicalAnalysis)
    news = _coerce_task_output(task_outputs[1], NewsDigest)
    recommendation = _coerce_task_output(task_outputs[2], FinalRecommendation)

    return AnalyzeResponse(
        ticker=normalized_ticker,
        model=model_name or os.getenv("GROQ_MODEL", DEFAULT_GROQ_MODEL),
        latency_seconds=latency_seconds,
        technicals=technicals,
        news=news,
        recommendation=recommendation,
    )

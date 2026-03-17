from __future__ import annotations

import os
from dataclasses import dataclass

from crewai import Agent, LLM

from tools import DuckDuckGoNewsTool, YFinanceTechnicalsTool

DEFAULT_GROQ_MODEL = "llama-3.3-70b-versatile"


def build_groq_llm(model_name: str | None = None) -> LLM:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("Missing GROQ_API_KEY. Add it to your environment or .env file.")

    resolved_model = model_name or os.getenv("GROQ_MODEL", DEFAULT_GROQ_MODEL)
    if not resolved_model.startswith("groq/"):
        resolved_model = f"groq/{resolved_model}"

    return LLM(
        model=resolved_model,
        api_key=api_key,
        temperature=0.1,
        max_tokens=900,
        timeout=8,
    )


@dataclass(slots=True)
class AgentBundle:
    data_miner: Agent
    news_sentinel: Agent
    quantitative_strategist: Agent

    def as_list(self) -> list[Agent]:
        return [self.data_miner, self.news_sentinel, self.quantitative_strategist]


def build_agents(llm: LLM) -> AgentBundle:
    data_miner = Agent(
        role="Data Miner",
        goal=(
            "Extract fresh technical signals for a stock ticker with minimal latency and return only "
            "the fields required by the schema."
        ),
        backstory=(
            "You are a market microstructure specialist. You trust tool outputs over intuition, avoid "
            "commentary that is not backed by data, and format your response to match the schema exactly."
        ),
        llm=llm,
        tools=[YFinanceTechnicalsTool()],
        verbose=False,
        allow_delegation=False,
        max_iter=1,
    )

    news_sentinel = Agent(
        role="News Sentinel",
        goal=(
            "Find only the last 24 hours of market-moving coverage that could affect the stock and "
            "return a concise structured digest."
        ),
        backstory=(
            "You operate like a low-latency market intelligence desk. You focus on catalysts, guidance, "
            "macro shocks, analyst actions, and regulatory developments while ignoring low-signal chatter."
        ),
        llm=llm,
        tools=[DuckDuckGoNewsTool()],
        verbose=False,
        allow_delegation=False,
        max_iter=1,
    )

    quantitative_strategist = Agent(
        role="Quantitative Strategist",
        goal=(
            "Synthesize technical indicators and news flow into a single recommendation with explicit "
            "confidence, catalysts, risks, and a practical action plan."
        ),
        backstory=(
            "You are a portfolio strategist optimizing for risk-adjusted decisions. You weigh recency, "
            "trend strength, and headline impact, and you never invent evidence that is not present in context."
        ),
        llm=llm,
        verbose=False,
        allow_delegation=False,
        max_iter=1,
    )

    return AgentBundle(
        data_miner=data_miner,
        news_sentinel=news_sentinel,
        quantitative_strategist=quantitative_strategist,
    )

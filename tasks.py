from __future__ import annotations

from crewai import Task

from agents import AgentBundle
from models import FinalRecommendation, NewsDigest, TechnicalAnalysis


def build_tasks(agents: AgentBundle, ticker: str) -> list[Task]:
    technicals_task = Task(
        description=(
            f"Analyze ticker {ticker}. Use the yfinance_technicals tool exactly once. Extract the latest "
            "price, RSI, moving averages, volume, and a defensible trend signal. Return only JSON that "
            "matches the TechnicalAnalysis schema."
        ),
        expected_output="A valid TechnicalAnalysis JSON object.",
        agent=agents.data_miner,
        output_pydantic=TechnicalAnalysis,
        async_execution=True,
    )

    news_task = Task(
        description=(
            f"Search the last 24 hours of market-moving coverage for ticker {ticker}. Use the "
            "duckduckgo_stock_news tool exactly once. Prioritize earnings, guidance, product launches, "
            "analyst actions, regulation, and macro headlines. Return only JSON that matches the "
            "NewsDigest schema."
        ),
        expected_output="A valid NewsDigest JSON object.",
        agent=agents.news_sentinel,
        output_pydantic=NewsDigest,
        async_execution=True,
    )

    strategist_task = Task(
        description=(
            f"Synthesize the technical analysis and news digest for ticker {ticker}. Produce a BUY, HOLD, "
            "or SELL recommendation with calibrated confidence, a clear time horizon, an evidence-based thesis, "
            "specific catalysts, specific risks, and an action plan. Use only the prior task outputs as evidence "
            "and return only JSON that matches the FinalRecommendation schema."
        ),
        expected_output="A valid FinalRecommendation JSON object.",
        agent=agents.quantitative_strategist,
        context=[technicals_task, news_task],
        output_pydantic=FinalRecommendation,
    )

    return [technicals_task, news_task, strategist_task]


def build_strategist_task(
    agents: AgentBundle,
    technicals: TechnicalAnalysis,
    news: NewsDigest,
) -> Task:
    technicals_json = technicals.model_dump_json(indent=2)
    news_json = news.model_dump_json(indent=2)

    return Task(
        description=(
            f"Synthesize the technical analysis and news digest for ticker {technicals.ticker}. "
            "Produce a BUY, HOLD, or SELL recommendation with calibrated confidence, a clear time horizon, "
            "an evidence-based thesis, specific catalysts, specific risks, and an action plan.\n\n"
            f"Technical analysis JSON:\n{technicals_json}\n\n"
            f"News digest JSON:\n{news_json}\n\n"
            "Use only the JSON evidence above and return only JSON that matches the FinalRecommendation schema."
        ),
        expected_output="A valid FinalRecommendation JSON object.",
        agent=agents.quantitative_strategist,
        output_pydantic=FinalRecommendation,
    )

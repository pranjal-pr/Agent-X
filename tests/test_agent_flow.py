from __future__ import annotations

import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from crewai import Process

from crew_service import analyze_stock
from models import FinalRecommendation, NewsDigest, TechnicalAnalysis
from tools import ResolvedStockQuery


def build_technicals() -> TechnicalAnalysis:
    return TechnicalAnalysis(
        ticker="NVDA",
        price=182.15,
        rsi_14=44.2,
        sma_20=180.8,
        sma_50=176.4,
        ema_20=181.1,
        volume=1250000,
        avg_volume_20=1500000,
        trend_signal="neutral",
        as_of="2026-03-18T00:00:00Z",
    )


def build_news() -> NewsDigest:
    return NewsDigest(
        ticker="NVDA",
        query="NVDA stock market news",
        items=[],
    )


def build_recommendation() -> FinalRecommendation:
    return FinalRecommendation(
        ticker="NVDA",
        stance="HOLD",
        confidence=0.62,
        time_horizon="swing",
        thesis="Momentum is mixed and the near-term setup favors waiting for confirmation before adding risk.",
        technical_summary="Price is near key moving averages and does not yet show a decisive breakout or breakdown.",
        news_summary="Recent headlines are supportive but not strong enough on their own to justify an aggressive position.",
        catalysts=["AI demand resilience", "Upcoming product roadmap"],
        risks=["Sector volatility", "Macro risk-off rotation"],
        action_plan="Wait for a cleaner breakout above resistance or a pullback into support before taking action.",
    )


def build_task_output(model: object) -> SimpleNamespace:
    return SimpleNamespace(pydantic=model)


class AgentFlowTests(unittest.TestCase):
    def test_analyze_stock_runs_all_three_agents_through_crewai(self) -> None:
        technicals = build_technicals()
        news = build_news()
        recommendation = build_recommendation()
        fake_bundle = MagicMock()
        fake_bundle.as_list.return_value = ["data-agent", "news-agent", "strat-agent"]
        fake_tasks = [object(), object(), object()]
        fake_result = SimpleNamespace(
            tasks_output=[
                build_task_output(technicals),
                build_task_output(news),
                build_task_output(recommendation),
            ]
        )
        fake_crew = MagicMock()
        fake_crew.kickoff.return_value = fake_result

        with (
            patch("crew_service.build_groq_llm", return_value=object()),
            patch("crew_service.build_agents", return_value=fake_bundle),
            patch(
                "crew_service.resolve_stock_query",
                return_value=ResolvedStockQuery(
                    query="nvda",
                    symbol="NVDA",
                    company_name="NVIDIA Corporation",
                ),
            ),
            patch("crew_service.build_tasks", return_value=fake_tasks) as mocked_build_tasks,
            patch("crew_service.Crew", return_value=fake_crew) as mocked_crew,
        ):
            response = asyncio.run(analyze_stock(" nvda "))

        mocked_build_tasks.assert_called_once_with(fake_bundle, "NVDA", "NVIDIA Corporation")
        fake_bundle.as_list.assert_called_once_with()
        mocked_crew.assert_called_once()
        crew_kwargs = mocked_crew.call_args.kwargs
        self.assertEqual(crew_kwargs["agents"], fake_bundle.as_list.return_value)
        self.assertEqual(crew_kwargs["tasks"], fake_tasks)
        self.assertEqual(crew_kwargs["process"], Process.sequential)
        self.assertEqual(response.ticker, "NVDA")
        self.assertEqual(response.technicals.ticker, "NVDA")
        self.assertEqual(response.news.ticker, "NVDA")
        self.assertEqual(response.recommendation.ticker, "NVDA")
        self.assertEqual(response.technicals.company_name, "NVIDIA Corporation")

    def test_analyze_stock_can_fall_back_to_task_output_attributes(self) -> None:
        technicals = build_technicals()
        news = build_news()
        recommendation = build_recommendation()
        fake_bundle = MagicMock()
        fake_bundle.as_list.return_value = ["data-agent", "news-agent", "strat-agent"]
        fake_tasks = [
            SimpleNamespace(output=build_task_output(technicals)),
            SimpleNamespace(output=build_task_output(news)),
            SimpleNamespace(output=build_task_output(recommendation)),
        ]
        fake_result = SimpleNamespace(tasks_output=[])
        fake_crew = MagicMock()
        fake_crew.kickoff.return_value = fake_result

        with (
            patch("crew_service.build_groq_llm", return_value=object()),
            patch("crew_service.build_agents", return_value=fake_bundle),
            patch(
                "crew_service.resolve_stock_query",
                return_value=ResolvedStockQuery(
                    query="NVDA",
                    symbol="NVDA",
                    company_name="NVIDIA Corporation",
                ),
            ),
            patch("crew_service.build_tasks", return_value=fake_tasks),
            patch("crew_service.Crew", return_value=fake_crew),
        ):
            response = asyncio.run(analyze_stock("NVDA"))

        self.assertEqual(response.technicals.trend_signal, "neutral")
        self.assertEqual(response.news.query, "NVDA stock market news")
        self.assertEqual(response.recommendation.stance, "HOLD")


if __name__ == "__main__":
    unittest.main()

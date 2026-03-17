from __future__ import annotations

import asyncio
import unittest
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from api import app, healthcheck
from models import AnalyzeRequest, AnalyzeResponse, AttachmentSummary, FinalRecommendation, NewsDigest, TechnicalAnalysis


def build_response(attachments: list[AttachmentSummary] | None = None) -> AnalyzeResponse:
    return AnalyzeResponse(
        ticker="NVDA",
        model="llama-3.3-70b-versatile",
        latency_seconds=3.2,
        attachments=attachments or [],
        technicals=TechnicalAnalysis(
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
        ),
        news=NewsDigest(ticker="NVDA", query="NVDA stock market news"),
        recommendation=FinalRecommendation(
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
        ),
    )


class AppSmokeTests(unittest.TestCase):
    def test_ticker_normalization_supports_common_symbols(self) -> None:
        payload = AnalyzeRequest(ticker=" brk.b ")
        self.assertEqual(payload.ticker, "BRK.B")

    def test_healthcheck_returns_ok(self) -> None:
        response = asyncio.run(healthcheck())
        self.assertEqual(response["status"], "ok")

    def test_expected_routes_exist(self) -> None:
        paths = {route.path for route in app.routes}
        self.assertIn("/", paths)
        self.assertIn("/api/health", paths)
        self.assertIn("/api/analyze", paths)

    def test_analyze_accepts_multipart_attachments(self) -> None:
        attachment = AttachmentSummary(
            filename="chart.png",
            media_type="image/png",
            size_bytes=4,
            kind="photo",
        )
        with patch("api.analyze_stock", new=AsyncMock(return_value=build_response([attachment]))) as mocked:
            client = TestClient(app)
            response = client.post(
                "/api/analyze",
                data={"ticker": "NVDA"},
                files=[("attachments", ("chart.png", b"data", "image/png"))],
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["attachments"][0]["filename"], "chart.png")
        self.assertEqual(mocked.await_args.kwargs["attachments"], [attachment])


if __name__ == "__main__":
    unittest.main()

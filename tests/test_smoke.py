from __future__ import annotations

import asyncio
import unittest

from api import app, healthcheck
from models import AnalyzeRequest


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


if __name__ == "__main__":
    unittest.main()

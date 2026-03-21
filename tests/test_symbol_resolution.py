from __future__ import annotations

import unittest
from unittest.mock import patch

from tools import resolve_stock_query


class SymbolResolutionTests(unittest.TestCase):
    def test_resolve_stock_query_prefers_best_equity_match_for_company_name(self) -> None:
        fake_quotes = [
            {
                "symbol": "TCS.NS",
                "shortname": "TATA CONSULTANCY SERV LT",
                "longname": "Tata Consultancy Services Limited",
                "exchange": "NSI",
                "quoteType": "EQUITY",
            },
            {
                "symbol": "TATAPOWER.NS",
                "shortname": "TATA POWER CO LTD",
                "longname": "Tata Power Company Limited",
                "exchange": "NSI",
                "quoteType": "EQUITY",
            },
        ]

        with patch("tools._search_quotes", return_value=fake_quotes):
            resolved = resolve_stock_query("tata consultancy services")

        self.assertEqual(resolved.symbol, "TCS.NS")
        self.assertEqual(resolved.company_name, "Tata Consultancy Services Limited")

    def test_resolve_stock_query_falls_back_to_symbol_when_search_is_empty(self) -> None:
        with patch("tools._search_quotes", return_value=[]):
            resolved = resolve_stock_query("BRK.B")

        self.assertEqual(resolved.symbol, "BRK.B")
        self.assertIsNone(resolved.company_name)


if __name__ == "__main__":
    unittest.main()

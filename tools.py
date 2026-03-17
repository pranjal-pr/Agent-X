from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pandas as pd
import yfinance as yf
from crewai.tools import BaseTool
from duckduckgo_search import DDGS
from pydantic import BaseModel, Field

from models import NewsDigest, NewsItem, TechnicalAnalysis

MARKET_DATA_TIMEOUT_SECONDS = 8
NEWS_SEARCH_TIMEOUT_SECONDS = 8


class TickerInput(BaseModel):
    ticker: str = Field(..., description="Public stock ticker symbol such as NVDA")


def _round_or_zero(value: Any, digits: int = 2) -> float:
    if value is None or pd.isna(value):
        return 0.0
    return round(float(value or 0), digits)


def _coerce_timestamp(value: Any) -> datetime:
    if isinstance(value, pd.Timestamp):
        if value.tzinfo is None:
            return value.tz_localize("UTC").to_pydatetime()
        return value.tz_convert("UTC").to_pydatetime()
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
    return datetime.now(timezone.utc)


def _compute_rsi(close_series: pd.Series, window: int = 14) -> float:
    delta = close_series.diff()
    gains = delta.clip(lower=0)
    losses = -delta.clip(upper=0)
    avg_gain = gains.rolling(window=window, min_periods=window).mean()
    avg_loss = losses.rolling(window=window, min_periods=window).mean()

    latest_gain = 0.0 if pd.isna(avg_gain.iloc[-1]) else float(avg_gain.iloc[-1])
    latest_loss = 0.0 if pd.isna(avg_loss.iloc[-1]) else float(avg_loss.iloc[-1])
    if latest_loss == 0:
        return 100.0 if latest_gain > 0 else 50.0

    rs = latest_gain / latest_loss
    return round(100 - (100 / (1 + rs)), 2)


def _trend_signal(price: float, sma_20: float, sma_50: float, rsi_14: float) -> str:
    if price > sma_20 > sma_50 and rsi_14 >= 55:
        return "bullish"
    if price < sma_20 < sma_50 and rsi_14 <= 45:
        return "bearish"
    return "neutral"


class YFinanceTechnicalsTool(BaseTool):
    name: str = "yfinance_technicals"
    description: str = (
        "Fetches recent market data for a stock ticker and returns price action, RSI, moving averages, "
        "and volume statistics as JSON."
    )
    args_schema: type[BaseModel] = TickerInput

    def _run(self, ticker: str) -> str:
        symbol = ticker.strip().upper()
        history = yf.download(
            symbol,
            period="6mo",
            interval="1d",
            auto_adjust=False,
            progress=False,
            threads=False,
            timeout=MARKET_DATA_TIMEOUT_SECONDS,
            multi_level_index=False,
        )
        if history.empty:
            raise ValueError(f"No market data returned for ticker '{symbol}'.")

        closes = history["Close"].dropna()
        volumes = history["Volume"].fillna(0)
        if len(closes) < 50:
            raise ValueError(f"Not enough price history to calculate indicators for '{symbol}'.")

        price = float(closes.iloc[-1])
        previous_close = float(closes.iloc[-2]) if len(closes) > 1 else price
        sma_20 = float(closes.tail(20).mean())
        sma_50 = float(closes.tail(50).mean())
        ema_20 = float(closes.ewm(span=20, adjust=False).mean().iloc[-1])
        rsi_14 = _compute_rsi(closes)
        avg_volume_20 = float(volumes.tail(20).mean())
        latest_timestamp = _coerce_timestamp(history.index[-1])
        technicals = TechnicalAnalysis(
            ticker=symbol,
            company_name=None,
            price=_round_or_zero(price),
            currency=None,
            change_percent=_round_or_zero(((price - previous_close) / previous_close) * 100, 2),
            rsi_14=rsi_14,
            sma_20=_round_or_zero(sma_20),
            sma_50=_round_or_zero(sma_50),
            ema_20=_round_or_zero(ema_20),
            volume=int(volumes.iloc[-1]),
            avg_volume_20=_round_or_zero(avg_volume_20),
            trend_signal=_trend_signal(price, sma_20, sma_50, rsi_14),
            as_of=latest_timestamp,
        )
        return technicals.model_dump_json(indent=2)


class DuckDuckGoNewsTool(BaseTool):
    name: str = "duckduckgo_stock_news"
    description: str = (
        "Searches DuckDuckGo for the last 24 hours of market news about a stock ticker and returns "
        "the most relevant items as JSON."
    )
    args_schema: type[BaseModel] = TickerInput

    def _run(self, ticker: str) -> str:
        symbol = ticker.strip().upper()
        query = f"{symbol} stock market news"
        items: list[NewsItem] = []
        results: list[dict[str, Any]] = []

        try:
            with DDGS(timeout=NEWS_SEARCH_TIMEOUT_SECONDS) as ddgs:
                results = list(
                    ddgs.news(
                        keywords=query,
                        region="wt-wt",
                        safesearch="moderate",
                        timelimit="d",
                        max_results=6,
                    )
                )

                if not results:
                    results = list(
                        ddgs.text(
                            keywords=query,
                            region="wt-wt",
                            safesearch="moderate",
                            timelimit="d",
                            max_results=6,
                        )
                    )
        except Exception:
            results = []

        for result in results[:6]:
            url = result.get("url") or result.get("href")
            title = result.get("title")
            if not url or not title:
                continue

            summary = result.get("body") or result.get("snippet") or "No summary available."
            items.append(
                NewsItem(
                    title=title.strip(),
                    source=result.get("source"),
                    url=url,
                    published_at=result.get("date"),
                    summary=summary.strip(),
                )
            )

        digest = NewsDigest(ticker=symbol, query=query, items=items)
        return digest.model_dump_json(indent=2)

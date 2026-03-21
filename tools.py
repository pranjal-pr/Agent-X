from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
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
SYMBOL_SEARCH_TIMEOUT_SECONDS = 8
MAX_NEWS_ITEMS = 4
MAX_SEARCH_QUOTES = 8


class ResolvedStockQuery(BaseModel):
    query: str
    symbol: str
    company_name: str | None = None


class TickerInput(BaseModel):
    ticker: str = Field(..., description="Public stock ticker symbol such as NVDA")
    company_name: str | None = Field(default=None, description="Optional company name hint for relevance")


def _normalize_lookup_text(value: str | None) -> str:
    return " ".join((value or "").strip().split()).casefold()


def _quote_score(query: str, quote: dict[str, Any], position: int) -> int:
    query_norm = _normalize_lookup_text(query)
    query_symbol_norm = query.replace(".", "").replace("-", "").replace(" ", "").casefold()
    symbol = (quote.get("symbol") or "").strip().upper()
    symbol_norm = symbol.replace(".", "").replace("-", "").casefold()
    shortname = quote.get("shortname") or ""
    longname = quote.get("longname") or ""
    exchange = (quote.get("exchange") or "").upper()
    score = max(0, 30 - position * 2)

    if (quote.get("quoteType") or "").upper() == "EQUITY":
        score += 200

    if symbol and query.strip().upper() == symbol:
        score += 400
    elif symbol_norm and query_symbol_norm == symbol_norm:
        score += 320

    exchange_bonus = {
        "NMS": 18,
        "NAS": 18,
        "NYQ": 18,
        "ASE": 16,
        "NSI": 20,
        "BSE": 18,
        "TOR": 12,
        "LSE": 10,
    }
    score += exchange_bonus.get(exchange, 0)

    for name in (shortname, longname):
        name_norm = _normalize_lookup_text(name)
        if not name_norm:
            continue
        if query_norm == name_norm:
            score += 260
        elif name_norm.startswith(query_norm):
            score += 220
        elif query_norm and all(token in name_norm for token in query_norm.split()):
            score += 150
        elif query_norm and query_norm in name_norm:
            score += 100

    return score


def _search_quotes(query: str) -> list[dict[str, Any]]:
    search = yf.Search(query=query, max_results=MAX_SEARCH_QUOTES)
    return list(getattr(search, "quotes", None) or [])


def resolve_stock_query(query: str) -> ResolvedStockQuery:
    cleaned_query = " ".join(query.strip().split())
    if not cleaned_query:
        raise ValueError("Enter a stock symbol or company name.")

    executor = ThreadPoolExecutor(max_workers=1)
    future = executor.submit(_search_quotes, cleaned_query)
    try:
        quotes = future.result(timeout=SYMBOL_SEARCH_TIMEOUT_SECONDS + 1)
    except FutureTimeoutError as exc:
        raise ValueError(f"Stock lookup timed out for '{cleaned_query}'.") from exc
    finally:
        executor.shutdown(wait=False, cancel_futures=True)

    ranked_quotes = sorted(
        (
            quote
            for quote in quotes
            if quote.get("symbol") and (quote.get("quoteType") or "").upper() == "EQUITY"
        ),
        key=lambda quote: _quote_score(cleaned_query, quote, quotes.index(quote)),
        reverse=True,
    )

    if not ranked_quotes:
        ranked_quotes = sorted(
            (quote for quote in quotes if quote.get("symbol")),
            key=lambda quote: _quote_score(cleaned_query, quote, quotes.index(quote)),
            reverse=True,
        )

    if ranked_quotes:
        best_match = ranked_quotes[0]
        return ResolvedStockQuery(
            query=cleaned_query,
            symbol=str(best_match["symbol"]).strip().upper(),
            company_name=(best_match.get("longname") or best_match.get("shortname") or None),
        )

    fallback_symbol = cleaned_query.upper()
    fallback_key = fallback_symbol.replace(".", "").replace("-", "")
    if fallback_key.isalnum():
        return ResolvedStockQuery(query=cleaned_query, symbol=fallback_symbol)

    raise ValueError(f"Could not match '{cleaned_query}' to a stock symbol.")


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

    @staticmethod
    def _download_history(symbol: str) -> pd.DataFrame:
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
        if not history.empty:
            return history

        return yf.Ticker(symbol).history(
            period="6mo",
            interval="1d",
            auto_adjust=False,
            timeout=MARKET_DATA_TIMEOUT_SECONDS,
        )

    def _run(self, ticker: str, company_name: str | None = None) -> str:
        symbol = ticker.strip().upper()
        executor = ThreadPoolExecutor(max_workers=1)
        future = executor.submit(self._download_history, symbol)
        try:
            history = future.result(timeout=MARKET_DATA_TIMEOUT_SECONDS + 1)
        except FutureTimeoutError as exc:
            raise ValueError(f"Market data request timed out for ticker '{symbol}'.") from exc
        finally:
            executor.shutdown(wait=False, cancel_futures=True)
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
            company_name=company_name.strip() if company_name else None,
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

    @staticmethod
    def _search_news(query: str) -> list[dict[str, Any]]:
        with DDGS(timeout=NEWS_SEARCH_TIMEOUT_SECONDS) as ddgs:
            results = list(
                ddgs.news(
                    keywords=query,
                    region="wt-wt",
                    safesearch="moderate",
                    timelimit="d",
                    max_results=MAX_NEWS_ITEMS,
                )
            )

            if not results:
                results = list(
                    ddgs.text(
                        keywords=query,
                        region="wt-wt",
                        safesearch="moderate",
                        timelimit="d",
                        max_results=MAX_NEWS_ITEMS,
                    )
                )
        return results

    def _run(self, ticker: str, company_name: str | None = None) -> str:
        symbol = ticker.strip().upper()
        company_hint = " ".join((company_name or "").split())
        search_anchor = " ".join(part for part in [company_hint, symbol] if part)
        query = f"{search_anchor} stock market news"
        items: list[NewsItem] = []
        results: list[dict[str, Any]] = []

        executor = ThreadPoolExecutor(max_workers=1)
        try:
            future = executor.submit(self._search_news, query)
            results = future.result(timeout=NEWS_SEARCH_TIMEOUT_SECONDS + 1)
        except FutureTimeoutError:
            results = []
        except Exception:
            results = []
        finally:
            executor.shutdown(wait=False, cancel_futures=True)

        for result in results[:MAX_NEWS_ITEMS]:
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

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class AnalyzeRequest(BaseModel):
    ticker: str = Field(..., min_length=1, max_length=10, description="Public stock ticker symbol")

    @field_validator("ticker")
    @classmethod
    def normalize_ticker(cls, value: str) -> str:
        normalized = value.strip().upper()
        stripped = normalized.replace(".", "").replace("-", "")
        if not stripped.isalnum():
            raise ValueError("Ticker must be alphanumeric.")
        return normalized


class TechnicalAnalysis(BaseModel):
    ticker: str
    company_name: str | None = None
    price: float = Field(..., gt=0)
    currency: str | None = None
    change_percent: float | None = None
    rsi_14: float = Field(..., ge=0, le=100)
    sma_20: float = Field(..., gt=0)
    sma_50: float = Field(..., gt=0)
    ema_20: float = Field(..., gt=0)
    volume: int = Field(..., ge=0)
    avg_volume_20: float = Field(..., ge=0)
    trend_signal: Literal["bullish", "neutral", "bearish"]
    as_of: datetime


class NewsItem(BaseModel):
    title: str
    source: str | None = None
    url: str
    published_at: str | None = None
    summary: str


class NewsDigest(BaseModel):
    ticker: str
    query: str
    items: list[NewsItem] = Field(default_factory=list)


class FinalRecommendation(BaseModel):
    ticker: str
    stance: Literal["BUY", "HOLD", "SELL"]
    confidence: float = Field(..., ge=0, le=1)
    time_horizon: Literal["intraday", "swing", "position"]
    thesis: str = Field(..., min_length=20)
    technical_summary: str = Field(..., min_length=20)
    news_summary: str = Field(..., min_length=20)
    catalysts: list[str] = Field(default_factory=list, min_length=2)
    risks: list[str] = Field(default_factory=list, min_length=2)
    action_plan: str = Field(..., min_length=20)


class AnalyzeResponse(BaseModel):
    ticker: str
    model: str
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    latency_seconds: float = Field(..., ge=0)
    technicals: TechnicalAnalysis
    news: NewsDigest
    recommendation: FinalRecommendation

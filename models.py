from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class AnalyzeRequest(BaseModel):
    ticker: str = Field(..., min_length=1, max_length=80, description="Public stock ticker symbol or company name")

    @field_validator("ticker")
    @classmethod
    def normalize_ticker(cls, value: str) -> str:
        normalized = " ".join(value.strip().split())
        if not normalized:
            raise ValueError("Enter a stock symbol or company name.")

        allowed_punctuation = {".", "-", "&", "'", " "}
        if any(not (character.isalnum() or character in allowed_punctuation) for character in normalized):
            raise ValueError("Use letters, numbers, spaces, dots, apostrophes, ampersands, or hyphens only.")

        stripped = normalized.replace(".", "").replace("-", "").replace(" ", "").replace("&", "").replace("'", "")
        if not stripped:
            raise ValueError("Enter a valid stock symbol or company name.")

        looks_like_ticker = " " not in normalized and all(
            character.isalnum() or character in {".", "-"} for character in normalized
        )
        return normalized.upper() if looks_like_ticker else normalized


class AttachmentSummary(BaseModel):
    filename: str
    media_type: str
    size_bytes: int = Field(..., ge=0)
    kind: Literal["file", "photo"]


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
    attachments: list[AttachmentSummary] = Field(default_factory=list)
    technicals: TechnicalAnalysis
    news: NewsDigest
    recommendation: FinalRecommendation

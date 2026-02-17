from pydantic import BaseModel
from typing import Optional
from datetime import date


class StockData(BaseModel):
    ticker: str
    price: float
    market_cap: float
    pe_ratio: Optional[float] = None
    forward_pe: Optional[float] = None
    revenue_ttm: Optional[float] = None
    earnings_ttm: Optional[float] = None
    debt_to_equity: Optional[float] = None
    dividend_yield: Optional[float] = None
    fifty_two_week_high: Optional[float] = None
    fifty_two_week_low: Optional[float] = None
    beta: Optional[float] = None
    short_percent_of_float: Optional[float] = None
    avg_volume: Optional[float] = None
    current_volume: Optional[float] = None
    analyst_target_price: Optional[float] = None
    analyst_recommendation: Optional[str] = None
    number_of_analysts: Optional[int] = None
    sector: str = "Unknown"
    industry: str = "Unknown"
    company_name: str = ""
    fetch_date: date = None

    def __init__(self, **data):
        if data.get("fetch_date") is None:
            data["fetch_date"] = date.today()
        super().__init__(**data)


class NewsItem(BaseModel):
    title: str
    source: str
    published_at: str
    summary: str
    sentiment: Optional[str] = None


class Alert(BaseModel):
    ticker: str
    alert_type: str
    severity: str
    message: str
    data: Optional[dict] = None
    timestamp: str = ""

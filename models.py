from pydantic import BaseModel
from typing import List, Optional

class MarketSummary(BaseModel):
    index_value: float
    change: float
    percent_change: float
    total_turnover: float
    total_trades: int
    total_scripts: int
    market_status: str
    timestamp: str

class CompanyPrice(BaseModel):
    symbol: str
    name: str
    price: float
    change: float
    percent_change: float
    volume: float
    timestamp: str

class GainerLoser(BaseModel):
    symbol: str
    price: float
    percent_change: float
    timestamp: str

class CompanyFundamentals(BaseModel):
    symbol: str
    name: str
    sector: str
    listed_date: str
    market_cap: str
    paid_up_capital: str
    high_low_52: str
    eps_ttm: float
    eps_reported: str
    pe_ratio: float
    pb_ratio: float
    roe: str
    book_value: float
    share_registrar: str
    website: str
    email: str
    contact: str
    head_office: str
    mgmt_head: str
    promoter_holding: str
    public_holding: str
    business_model: str
    management_quality: str
    industry_strength: str
    future_growth: str
    timestamp: str

class OHLCPoint(BaseModel):
    time: int
    open: float
    high: float
    low: float
    close: float
    volume: float

class SectorData(BaseModel):
    sector: str
    index_value: float
    change: float
    percent_change: float
    timestamp: str

class APIKey(BaseModel):
    key: str
    features: List[str] = ["all"]
    created_at: str
    last_used: Optional[str] = None

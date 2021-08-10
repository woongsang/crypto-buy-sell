from pydantic import BaseModel
from typing import Optional


class ExchangeAccountModel(BaseModel):
    exchange_name: str
    api_key: str
    secret_key: str
    username: Optional[str] = None
    slack_url: Optional[str] = None


class LarrySessionModel(BaseModel):
    exchange_account_id: str
    market: str
    x: float
    cycle_hours: int
    position: int
    buy_percentage: float
    stop_loss_percentage: float = 5
    leverage_times: int = 1
    slippage_percentage: float = 0.1
    entry_price: float = None
    close_timestamp: Optional[str] = None

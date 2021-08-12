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
    exchange: str
    market: str
    x: float
    cycle_hours: int
    in_position_hours: int
    entry_percentage: float
    sl_tp_percentage: float
    leverage_times: int
    slippage_percentage: float

    long_target_price: float = None
    short_target_price: float = None
    sl_tp_price: float = None
    close_timestamp: int = None  # position end time
    reset_timestamp: int = None
    position: int = None
    coin_amount: int = None
    update_timestamp: int = None

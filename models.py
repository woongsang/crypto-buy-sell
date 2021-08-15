from pydantic import BaseModel
from typing import Optional


class ExchangeAccount(BaseModel):
    exchange_name: str
    api_key: str
    secret_key: str
    username: Optional[str] = None
    slack_url: Optional[str] = None


class RequestApi(BaseModel):
    id: str
    url: str
    elements: str


class LarrySession(BaseModel):
    exchange_account_id: str
    exchange: str
    market: str
    x: float
    cycle_hours: int
    sliding_hours: int
    in_position_hours: int
    entry_percentage: float
    stop_loss_percentage: float
    leverage_times: int
    slippage_percentage: float

    long_target_price_dict: dict = None
    short_target_price_dict: dict = None

    stop_loss_price: float = None

    close_timestamp: int = None  # position end time
    position: int = None
    coin_amount: int = None
    update_timestamp: int = None

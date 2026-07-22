"""
Base Broker Interface

All broker adapters must implement this interface for seamless switching.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional


@dataclass
class BrokerOrder:
    id: str = ""
    broker_order_id: str = ""
    symbol: str = ""
    type: str = ""  # MARKET, LIMIT, SL, SL-M
    side: str = ""  # BUY, SELL
    quantity: int = 0
    filled_quantity: int = 0
    price: Optional[float] = None
    trigger_price: Optional[float] = None
    average_price: Optional[float] = None
    status: str = "PENDING"
    rejected_reason: Optional[str] = None
    exchange: str = "NSE"
    product: str = "MIS"
    validity: str = "DAY"
    filled_at: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class BrokerPosition:
    symbol: str
    quantity: int
    average_price: float
    last_price: float
    pnl: float = 0.0
    pnl_percent: float = 0.0
    multiplier: float = 1.0
    exchange: str = "NSE"


@dataclass
class BrokerHolding:
    symbol: str
    quantity: int
    average_price: float
    last_price: float
    pnl: float = 0.0
    holding_type: str = "delivery"


@dataclass
class BrokerFunds:
    total_margin: float = 0.0
    used_margin: float = 0.0
    available_margin: float = 0.0
    opening_balance: float = 0.0
    day_pnl: float = 0.0
    total_pnl: float = 0.0


@dataclass
class BrokerOrderStatus:
    order_id: str
    status: str
    filled_quantity: int = 0
    pending_quantity: int = 0
    average_price: Optional[float] = None
    rejected_reason: Optional[str] = None


class BaseBroker(ABC):
    """Abstract base class for all broker adapters."""

    @abstractmethod
    async def connect(self) -> bool:
        """Establish connection to broker API."""
        ...

    @abstractmethod
    async def login(self) -> bool:
        """Authenticate with broker."""
        ...

    @abstractmethod
    async def logout(self) -> bool:
        """Logout from broker."""
        ...

    @abstractmethod
    async def place_order(self, order: BrokerOrder) -> BrokerOrder:
        """Place an order."""
        ...

    @abstractmethod
    async def modify_order(self, order_id: str, order: BrokerOrder) -> BrokerOrder:
        """Modify an existing order."""
        ...

    @abstractmethod
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an order."""
        ...

    @abstractmethod
    async def get_positions(self) -> list[BrokerPosition]:
        """Get current open positions."""
        ...

    @abstractmethod
    async def get_holdings(self) -> list[BrokerHolding]:
        """Get holdings."""
        ...

    @abstractmethod
    async def get_orders(self) -> list[BrokerOrder]:
        """Get all orders."""
        ...

    @abstractmethod
    async def get_order_status(self, order_id: str) -> BrokerOrderStatus:
        """Get order status."""
        ...

    @abstractmethod
    async def get_margin(self) -> BrokerFunds:
        """Get margin/funds data."""
        ...

    @abstractmethod
    async def get_funds(self) -> BrokerFunds:
        """Get funds summary."""
        ...

    @abstractmethod
    async def get_name(self) -> str:
        """Return broker display name."""
        ...

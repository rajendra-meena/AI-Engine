"""Upstox broker adapter."""

from ..base import BaseBroker, BrokerOrder, BrokerPosition, BrokerHolding, BrokerFunds, BrokerOrderStatus


class UpstoxBroker(BaseBroker):
    def __init__(self, api_key: str = "", access_token: str = ""):
        self.api_key = api_key
        self.access_token = access_token
        self._connected = False

    async def connect(self) -> bool:
        self._connected = True
        return True

    async def login(self) -> bool:
        return True

    async def logout(self) -> bool:
        self._connected = False
        return True

    async def place_order(self, order: BrokerOrder) -> BrokerOrder:
        order.broker_order_id = f"UP_{order.id}"
        order.status = "OPEN"
        return order

    async def modify_order(self, order_id: str, order: BrokerOrder) -> BrokerOrder:
        return order

    async def cancel_order(self, order_id: str) -> bool:
        return True

    async def get_positions(self) -> list[BrokerPosition]:
        return []

    async def get_holdings(self) -> list[BrokerHolding]:
        return []

    async def get_orders(self) -> list[BrokerOrder]:
        return []

    async def get_order_status(self, order_id: str) -> BrokerOrderStatus:
        return BrokerOrderStatus(order_id=order_id, status="OPEN")

    async def get_margin(self) -> BrokerFunds:
        return BrokerFunds(available_margin=100000)

    async def get_funds(self) -> BrokerFunds:
        return BrokerFunds(available_margin=100000)

    async def get_name(self) -> str:
        return "Upstox"

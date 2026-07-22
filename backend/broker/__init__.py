"""
Broker Integration Layer

Abstract interface and concrete adapters for institutional broker APIs.
All broker implementations follow the same interface for seamless switching.
"""

from .base import BaseBroker, BrokerOrder, BrokerPosition, BrokerHolding, BrokerFunds, BrokerOrderStatus

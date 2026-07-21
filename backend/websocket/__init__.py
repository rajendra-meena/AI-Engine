"""
MarketMind AI — WebSocket Gateway

Real-time communication layer between backend and connected clients.

Architecture:
    Connected Clients (browsers, apps)
        │
        ▼
    WebSocket Gateway  ← manages connections, subscriptions, broadcast
        │
        ├── ConnectionManager   ← tracks clients, heartbeats, auth
        ├── SubscriptionManager ← per-client channel/symbol subscriptions
        └── EventBus subscriber ← forwards internal events to WS clients

    No trading logic, no data fetching.
    Pure transport layer.
"""

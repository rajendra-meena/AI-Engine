"""
AI Decision Intelligence Engine — Institutional Decision Framework

Architecture:
    7 Lower Engines → AI Decision Engine
                           │
         ┌──────────┬──────────┬──────────┬──────────┐
         │ Score    │Confidence│  Risk    │  Trade   │
         │ Engine   │  Engine  │  Engine  │  Planner │
         └────┬─────┴────┬─────┴────┬─────┴────┬─────┘
              │          │          │          │
              └──────────┴──────────┴──────────┘
                           │
                      Orchestrator
                           │
                    DecisionSnapshot
"""
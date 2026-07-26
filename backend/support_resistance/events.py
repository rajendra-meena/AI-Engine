"""SR Engine events.

Canonical events:
    SUPPORT_RESISTANCE_UPDATED — Published after each successful SR calculation.
    Carries candle_version and analysis_cycle_id from the originating candle.
"""

# Canonical event (replaces legacy S_UPDATED)
SUPPORT_RESISTANCE_UPDATED = "support_resistance_updated"

# Legacy alias for backward compatibility
S_UPDATED = SUPPORT_RESISTANCE_UPDATED

# Sub-events (legacy, kept for existing subscribers)
S_RESISTANCE_UPDATED = "sr_resistance_updated"
S_SUPPLY_ZONE_CREATED = "sr_supply_zone_created"
S_DEMAND_ZONE_CREATED = "sr_demand_zone_created"
S_BREAKOUT_DETECTED = "sr_breakout_detected"
S_RETEST_DETECTED = "sr_retest_detected"
S_FALSE_BREAKOUT = "sr_false_breakout"
S_LEVEL_BROKEN = "sr_level_broken"

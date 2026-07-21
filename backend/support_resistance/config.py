"""SR Engine configuration."""

# Merge tolerance: nearby levels within this % are combined
MERGE_TOLERANCE = 0.0008  # 0.08%

# Psychological level spacing
PSYCHOLOGICAL_SPACING = 100  # NIFTY/BANKNIFTY levels every 100 points

# Zone strength thresholds
STRONG_TOUCHES = 3
NORMAL_TOUCHES = 2
WEAK_TOUCHES = 1

# Max historical snapshots
HISTORY_LIMIT = 500

# Zone expiry: zones older than this many candles are archived
ZONE_MAX_AGE = 200

"""Approximate rate cards used to ESTIMATE fares from route distance and time.

These are NOT official provider prices. They are rough Bengaluru-style figures
so the comparison reacts to the real route. Check them against what the apps
actually charge and edit the numbers below; nothing else needs to change.

fare = max(min_fare, (base + per_km * max(km - free_km, 0) + per_min * minutes) * markup)
"""

RATE_CARDS = [
    # provider, ride_type, base, free_km, per_km, per_min, min_fare, markup, speed_factor
    ("Namma Yatri", "auto",    30, 2, 15, 0.0,  30, 1.00, 1.00),
    ("Ola",         "auto",    30, 2, 15, 0.0,  30, 1.08, 1.00),
    ("Uber",        "auto",    30, 2, 15, 0.0,  30, 1.12, 1.00),
    ("Rapido",      "auto",    30, 2, 15, 0.0,  30, 1.05, 1.00),
    ("Rapido",      "bike",    20, 0,  7, 0.5,  30, 1.00, 0.85),
    ("Uber",        "bike",    20, 0,  7.5, 0.5, 35, 1.00, 0.85),
    ("Ola",         "bike",    20, 0,  7, 0.5,  30, 1.00, 0.85),
    ("Ola",         "sedan",   50, 0, 13, 1.5, 100, 1.00, 1.00),
    ("Uber",        "sedan",   50, 0, 14, 1.5, 110, 1.00, 1.00),
    ("Uber",        "premium", 70, 0, 18, 2.0, 160, 1.00, 1.00),
]

LOW_FACTOR = 0.90   # shown as the low end of the range
HIGH_FACTOR = 1.20  # high end, allows for demand-based surge

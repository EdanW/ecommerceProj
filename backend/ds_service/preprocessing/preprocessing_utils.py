import pandas as pd

def encode_intensity(intensity_str):
    """
    Maps intensity to 0-3 scale.
    0 = Unknown/None
    1 = Low
    2 = Medium
    3 = High
    """
    if not intensity_str:
        return 0
        
    mapping = {
        "low": 1,
        "medium": 2,
        "high": 3,
        "very high": 3 # Cap at 3
    }
    return mapping.get(intensity_str.lower(), 0) # Default to 0 (Unknown)

def encode_time_of_day(time_str):
    """
    Maps time of day to 0-3 scale.
    0 = Unknown
    1 = Morning
    2 = Afternoon
    3 = Evening
    4 = Night
    """
    if not time_str:
        return 0
        
    mapping = {
        "morning": 1,
        "afternoon": 2,
        "evening": 3,
        "night": 4
    }
    return mapping.get(time_str.lower(), 0) # Default to 0

def encode_trend(trend_str):
    """
    Maps trend to -1 (Falling), 0 (Stable), 1 (Rising).
    """
    mapping = {"falling": -1, "stable": 0, "rising": 1}
    return mapping.get(trend_str.lower(), 0)


from typing import List, Dict, Any

def _analyze_glucose_trend(history: List[dict]) -> tuple:
    """
    Helper to calculate average and trend from history list.
    Assumes history is sorted Newest -> Oldest
    Returns: avg_glucose, trend
    """
    if not history:
        # Fallback if no history exists
        return 0, "stable"

    # 1. Extract values
    values = [item['glucose_mg_dl'] for item in history]
    
    # 2. Calculate Average
    avg_glucose = sum(values) / len(values)

    # 3. Calculate Trend (Newest - Oldest)
    # We assume index 0 is the most recent (21:30) and index -1 is oldest (17:00)
    newest = values[0]
    oldest = values[-1]
    delta = newest - oldest

    # Define a threshold for "trend" (e.g., change > 10mg/dl)
    if delta > 10:
        trend = "rising"
    elif delta < -10:
        trend = "falling"
    else:
        trend = "stable"

    avg_glucose_int = int(avg_glucose)
    return avg_glucose_int, trend
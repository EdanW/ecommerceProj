from typing import List

def _analyze_glucose_trend(history: List[dict]) -> tuple:
    """
    Computes the rolling glucose average and directional trend from a reading history.

    Expects history sorted newest-first (index 0 = most recent reading).
    Trend is derived from the delta between the most recent and oldest readings:
      > +10 mg/dL → "rising", < -10 mg/dL → "falling", otherwise → "stable".

    Returns: (avg_glucose_int, trend_str)
    """
    if not history:
        return 0, "stable"

    values = [item['glucose_mg_dl'] for item in history]
    avg_glucose = sum(values) / len(values)

    delta = values[0] - values[-1]
    if delta > 10:
        trend = "rising"
    elif delta < -10:
        trend = "falling"
    else:
        trend = "stable"

    return int(avg_glucose), trend
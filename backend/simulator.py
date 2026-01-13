import random


def get_current_glucose_level():
    # Simulating a mock glucose stream.
    # In a real app, this would connect to a sensor API.
    # Returns a value between 70 (low) and 180 (spike)
    base_glucose = 110
    fluctuation = random.randint(-30, 40)
    current_level = base_glucose + fluctuation

    status = "Normal"
    if current_level < 80:
        status = "Low"
    elif current_level > 140:
        status = "Elevated"

    return {"level": current_level, "status": status}
from __future__ import annotations
from typing import Any
from .crew import sneaker_research_crew
from .utils import get_date_range

# Change number of items
num_items = 2

today, cutoff = get_date_range()

if __name__ == "__main__":
    result = sneaker_research_crew.kickoff(
        inputs={
            "today": today.isoformat(),
            "cutoff_date": cutoff.isoformat(),
            "num_items": num_items
        }
    )
from __future__ import annotations
from crewai import Task
from .models import ScoutOutput, AnalystOutput
from .agents import sneaker_scout, sneaker_market_analyst

sneaker_scout_task = Task(
    description="""
    Compile information on upcoming sneaker releases by scraping information from reputable release calendars on
    sites such as https://www.sneakerfiles.com/release-dates/, nicekicks.com, sneakernews.com, and goat.com. Find and navigate to the release calendar pages on each site
    to find organized information on upcoming releases.

    Today is {today}. Only include releases between {today} and {cutoff_date}.

    Deliverable: Return up to {num_items} releases ordered by the soonest upcoming release.
    """,
    expected_output="""ScoutOutput with exactly {num_items} upcoming sneaker releases in the date window, each with 1–2 sources. You're outputted
    items should closely match the items on the release calendars of the sites.""",
    output_pydantic=ScoutOutput,
    agent=sneaker_scout,
)

sneaker_market_analyst_task = Task(
    description="""
    Analyze all sneaker releases given and predict resale price + confidence (0-100).

    Research similar past releases on StockX. Use historical prices of same model/line.
    Don't use pre-release prices (inflated).

    Confidence: 75-100=high (clear trend, ±$20), 50-75=moderate, 25-50=uncertain, 0-25=unique/no data.

    Limit: Max 2 searches per item. Use your knowledge when data is unavailable.

    Output: AnalystOutput with resale_estimate and confidence_score for each item.
    """,
    expected_output="""
    AnalystOutput with predictions for all items.
    """,
    output_pydantic=AnalystOutput,
    agent=sneaker_market_analyst,
    context=[sneaker_scout_task],
)
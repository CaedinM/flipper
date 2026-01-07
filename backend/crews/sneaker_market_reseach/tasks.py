from __future__ import annotations
from crewai import Task
from .models import ScoutOutput, AnalystOutput
from .agents import build_scout_agent, build_analyst_agent


def build_tasks():
    scout_agent = build_scout_agent()
    analyst_agent = build_analyst_agent()
    
    sneaker_scout_task = Task(
        description="""
        Compile information on upcoming sneaker releases by scraping information from reputable release calendars on
        sites such as https://www.sneakerfiles.com/release-dates/, nicekicks.com, sneakernews.com, and goat.com. Find and navigate to the release calendar pages on each site
        to find organized information on upcoming releases.
        
        - Today is {today}. Only include releases between {today} and {cutoff_date}.

        Deliverable: Return up to {num_items} releases ordered by the soonest upcoming release.
        """,
        expected_output="""ScoutOutput with exactly {num_items} upcoming sneaker releases in the date window, each with 1–2 sources. You're outputted
        items should closely match the items on the release calendars of the sites.""",
        output_pydantic=ScoutOutput,
        agent=sneaker_scout,
    )

    sneaker_market_analyst_task = Task(
        description="""
        Given a list of upcoming sneaker releases, do research and analyze each item one by one to come up with a resell price prediction
        and confidence score for that prediction.
        Consider historical trends and the performance of similar sneakers (same model or release type (collaboration, limited release etc.)
        Use StockX sale price as the most reliable indicator for fair resale value.
        Based on your research, make a resell price prediction. If you are considering a wide range of values, choose the 50th percentile value
        and lower your confidence score.
        If you can't find similar items, or there is no history of consistent price trends for similar items, lower your confidence score
        significantly.

        Confidence Score Rubric:
        75-100: Highly confident that the show will consistently resell within $20 of the resale prediction. There is a clear trend of 
        very similar items reselling at this price, and there are little to no factors that could cause this item not to follow that trend
        and closely match the prediction.
        50-75: Moderately confident that the resale prediction is accurate, but potential outside factors could cause the prediction to 
        be incorrect.
        25-50: You are mostly unsure about this prediction. Price trends for similar items are inconsistent, or the item is unique and
        hard to compare to other releases. 
        0-25: This is a truly unique release and incomparable to anything else. You have very little confidence in your resale estimate.

        Important note: Using StockX sale value for the exact item you are analyzing is not reliable because the item has not released to 
        the public yet and pre-release prices are always inflated.
        Instead, look at prices for previously released items of the same model or line as the sneaker you are analyzing. Use your intuition
        about what makes items popular, to evaluate unique items such as collaborations, and limited releases.

        Deliverable: For each item in the given list, generate a resale price prediction of what you think the item will sell for on the
        secondary resell market within one month of purchase and a confidence score based on how confident you are in that prediction.
        You will output AnalystOutput with predictions and confidence scores for all items provided in the original list.
        """,
        expected_output="""
        AnalystOutput with the same number of items as the original given list, including resale price predictions and confidence scores
        for each item.
        """,
        output_pydantic=AnalystOutput,
        agent=sneaker_market_analyst,
        context=[sneaker_scout_task],
    )

    return sneaker_scout_task, sneaker_market_analyst_task
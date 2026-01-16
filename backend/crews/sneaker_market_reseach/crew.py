from __future__ import annotations
from crewai import Crew, Process
from .agents import sneaker_scout, sneaker_market_analyst
from .tasks import sneaker_scout_task, sneaker_market_analyst_task

sneaker_research_crew = Crew(
    agents=[sneaker_scout, sneaker_market_analyst],
    tasks=[sneaker_scout_task, sneaker_market_analyst_task],
    process=Process.sequential,
    verbose=False,
)
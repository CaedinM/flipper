from __future__ import annotations
from crewai import Crew, Process
from .tasks import build_tasks

def build_crew() -> Crew:
    sneaker_scout_task, sneaker_market_analyst_task = build_tasks()
    return Crew(
        agents=[sneaker_scout_task.agent, sneaker_market_analyst_task.agent],
        tasks=[sneaker_scout_task, sneaker_market_analyst_task],
        process=Process.sequential,
        verbose=True,
    )
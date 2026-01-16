from __future__ import annotations
from crewai import Agent, LLM
from .tools import search_tool, scrape_tool

from dotenv import load_dotenv
import os
from pathlib import Path

# Load .env from project root (4 levels up from agents.py)
project_root = Path(__file__).parent.parent.parent.parent
env_path = project_root / ".env"
if env_path.exists():
    load_dotenv(str(env_path), override=True)

OPENAI_API_KEY = os.getenv("OPEN_AI_API_KEY")
llm = LLM(model="gpt-4o-mini", api_key=OPENAI_API_KEY)

sneaker_scout = Agent(
    role="Upcoming Sneaker Release Scout",
    goal="""Identify upcoming sneaker releases.""",
    backstory="""
    You are a master web scraper who is highly resourceful and can easily navigate the internet to find relevant information and 
    Extract it in easily ingestible formats. You do not get distracted by irrelevant articles/information.
    """,
    tools=[search_tool, scrape_tool],
    llm=llm,
    verbose=True,
    allow_delegation=False,
)

sneaker_market_analyst = Agent(
    role="Sneaker Resell Market Analyst",
    goal="Accurately project resale values for upcoming sneaker releases",
    backstory="""You are a long-time sneaker reseller and hypebeast. You have an expert understanding of how cultural trends,
    historical performance and market factors impact the potential profitability of sneakers on the secondary market.""",
    tools=[search_tool, scrape_tool],
    llm=llm,
    verbose=True,
    allow_delegation=False,
)
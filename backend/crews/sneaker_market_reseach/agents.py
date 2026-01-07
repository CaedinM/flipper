from __future__ import annotations
from crewai import Agent

def build_sneaker_scout() -> Agent:
    return Agent(
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

def build_sneaker_market_analyst() -> Agent:
    return Agent(
    role="Sneaker Resell Market Analyst",
    goal="Accurately project resale values for upcoming sneaker releases",
    backstory="""You are a long-time sneaker reseller and hypebeast. You have an expert understanding of how cultural trends,
    historical performance and market factors impact the potential profitability of sneakers on the secondary market.""",
    tools=[search_tool, scrape_tool],
    llm=llm,
    verbose=True,
    allow_delegation=False,
)
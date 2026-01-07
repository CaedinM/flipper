from __future__ import annotations
from typing import Any
import json
from .crew import build_crew
from .models import ScoutOutput, AnalystOutput

from dotenv import load_dotenv
import os

# Load .env.local from project root
# Notebook is at: backend/crews/sneaker_market_reseach/notebooks/
# Project root is 4 levels up: ../../../../.env.local
load_dotenv("../../../../.env.local", override=True)

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
OPENAI_API_KEY = os.getenv("OPEN_AI_API_KEY")

search_tool = TavilySearchTool(api_key=TAVILY_API_KEY)
scrape_tool = ScrapeWebsiteTool()  
llm = LLM(model="gpt-4o", api_key=OPENAI_API_KEY)

# define date
from datetime import date, timedelta
today = date.today()
cutoff = today + timedelta(days=21)
window_month = date.today()

# Change number of items
num_items = 3 

crew = build_crew()

result = crew.kickoff(
    inputs={
        "today": today.isoformat(),
        "cutoff_date": cutoff.isoformat(),
        "num_items": num_items
    }
)
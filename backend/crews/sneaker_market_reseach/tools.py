from crewai_tools import TavilySearchTool, ScrapeWebsiteTool
from dotenv import load_dotenv
import os
from pathlib import Path

# Load .env.local from project root (4 levels up from tools.py)
project_root = Path(__file__).parent.parent.parent.parent
env_path = project_root / ".env.local"
load_dotenv(str(env_path), override=True)

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

search_tool = TavilySearchTool(api_key=TAVILY_API_KEY)

scrape_tool = ScrapeWebsiteTool()  
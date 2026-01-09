# 🦭 Flipper — All-in-One Resell Analytics Platform

Flipper is an **AI-powered resale analytics platform** designed for modern resellers of collectibles, sneakers, tickets, and limited-release goods. It combines **inventory tracking, order logging, profitability analytics, and AI-driven market research** into a single streamlined workflow.

This project blends **data engineering, product analytics, and autonomous AI agents** to help users identify high-value opportunities and track performance over time.

---

## Key Features

### Inventory & Order Management
- Log purchases and sales with full cost basis tracking
- Automatically update inventory levels
- Support for new items added dynamically at order time
- PostgreSQL-backed relational schema for long-term data integrity

### Analytics Dashboard (Streamlit)
- Revenue, profit, and margin tracking
- Monthly KPIs and trends
- Item-level performance breakdowns
- Interactive charts (Altair)

### AI Market Research Agents (CrewAI)
- Autonomous agents scan upcoming drops and releases
- Evaluate resale potential using:
  - Brand demand
  - Scarcity
  - Historical resale behavior
- Rank opportunities by expected ROI

---

## Tech Stack

**Backend & Data**
- Python
- PostgreSQL
- psycopg2

**Frontend**
- Streamlit
- Altair
- Pandas

**AI & Agents**
- CrewAI
- LLM-powered market research agents

**Dev Tools**
- Conda / venv
- Git & GitHub

---

## Project Structure

```bash
flipper/
├── backend/                           # Backend services and data layer
│   ├── db.py                          # Database access layer
│   ├── sql/                           # SQL schema and queries
│   │   ├── schema.sql                 # PostgreSQL schema
│   │   └── releases.sql               # Release tracking schema
│   └── crews/                         # CrewAI agent crews
│       └── sneaker_market_reseach/
│           ├── __init__.py
│           ├── agents.py              # CrewAI agent definitions
│           ├── crew.py                # Crew configuration
│           ├── main.py                # Main entry point for crew execution
│           ├── models.py              # Pydantic models for agent outputs
│           ├── tasks.py               # CrewAI task definitions
│           ├── tools.py               # Agent tools (search, scrape, etc.)
│           ├── utils.py               # Utility functions
│           └── notebooks/             # Jupyter notebooks for testing
│               └── test_market_research_crew.ipynb
├── frontend/                          # Streamlit frontend application
│   ├── app.py                         # Main Streamlit entry point (Overview)
│   ├── state.py                       # Session state management
│   ├── assets/                        # Static assets
│   │   └── flipper_logo.png
│   ├── components/                    # Reusable UI components
│   │   ├── charts.py                  # Altair chart definitions
│   │   ├── new_order_form.py          # Order entry form component
│   │   ├── new_sale_form.py           # Sale entry form component
│   │   ├── sale_details.py            # Sale details display component
│   │   └── utils.py                   # Component utilities
│   └── pages/                         # Streamlit multipage views
│       ├── AI_Market_Insights.py      # AI market research page
│       ├── Inventory.py               # Inventory management page
│       ├── Orders_&_Expenses.py       # Orders and expenses page
│       └── Sales.py                   # Sales tracking page
├── requirements.txt                   # Python dependencies
└── README.md


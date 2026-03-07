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
- Docker
- Git & GitHub

---

## Getting Started

```bash
# 1. Clone the repo
git clone https://github.com/CaedinM/flipper.git
cd flipper

# 2. Set up environment
cp .env.example .env
# Edit .env to set DB_PASSWORD

# 3. Run with Docker
docker-compose up --build

# 4. Open the app
# http://localhost:8501
```

---

## Project Structure

```
flipper/
├── backend/
│   ├── crews/          # DB helpers for agent runs
│   ├── scrapers/       # Release calendar scrapers (sneakers, Pokemon)
│   ├── sql/            # Database schema and triggers
│   └── db.py           # Query functions and DB connection
├── frontend/
│   ├── assets/         # Static assets (logo, images)
│   ├── components/     # Reusable UI components and forms
│   ├── pages/          # Streamlit pages (Inventory, Sales, Orders, Insights, Calendars)
│   ├── Overview.py     # Main dashboard page
│   └── state.py        # Session state initialization
├── docker/
│   └── init-db/        # Database initialization scripts
├── initial_data/       # Seed CSVs for initial data import
├── Dockerfile
├── docker-compose.yml
└── requirements.txt


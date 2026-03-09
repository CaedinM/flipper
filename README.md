# 🦭 Flipper — All-in-One Resell Analytics Platform

Flipper is a **resale analytics platform** designed for modern resellers of collectibles, sneakers, tickets, and limited-release goods. It combines **inventory tracking, order logging, deep profitability analytics, and automated release calendar scraping** into a single streamlined workflow.

---

## Key Features

### Inventory & Order Management
- Log purchases and sales with full cost basis tracking
- Automatically update inventory levels
- Support for new items added dynamically at order time
- PostgreSQL-backed relational schema for long-term data integrity

### Analytics Dashboard (Streamlit)
- Revenue, profit, and margin tracking across all categories
- Monthly KPIs and trend charts
- Item-level and platform-level performance breakdowns
- Cost breakdown analysis — PAS fees, shipping, and other expenses
- Profit margin by category and by selling platform
- Interactive charts (Altair)

### Insights Page
- Side-by-side profit margin breakdowns by **category** and **platform**
- Full expense breakdown with totals for fees, shipping, and miscellaneous costs
- Designed to surface where money is being made — and where it's being lost

### Release Calendars (Web Scrapers)
- Automated scrapers pull upcoming drop schedules for:
  - **Sneakers** — upcoming releases with retail and estimated resale data
  - **Pokémon** — upcoming set and product release dates
- Data is stored and displayed in dedicated calendar pages for quick reference

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

**Scrapers**
- Custom Python scrapers for sneaker and Pokémon release calendars

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
│   ├── crews/          # DB helpers (legacy)
│   ├── scrapers/       # Release calendar scrapers (sneakers, Pokemon)
│   ├── sql/            # Database schema and triggers
│   └── db.py           # Query functions and DB connection
├── frontend/
│   ├── assets/         # Static assets (logo, images)
│   ├── components/     # Reusable UI components and forms
│   ├── pages/          # Streamlit pages (Inventory, Insights, Sales, Orders, Calendars)
│   ├── Overview.py     # Main dashboard page
│   └── state.py        # Session state initialization
├── docker/
│   └── init-db/        # Database initialization scripts
├── initial_data/       # Seed CSVs for initial data import
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

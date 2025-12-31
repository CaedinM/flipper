# 🦭 Flipper — All-in-One Resell Analytics Platform

Flipper is an **AI-powered resale analytics platform** designed for modern resellers of collectibles, sneakers, tickets, and limited-release goods. It combines **inventory tracking, order logging, profitability analytics, and AI-driven market research** into a single streamlined workflow.

This project blends **data engineering, product analytics, and autonomous AI agents** to help users identify high-value opportunities and track performance over time.

---

## 🚀 Key Features

### 📦 Inventory & Order Management
- Log purchases and sales with full cost basis tracking
- Automatically update inventory levels
- Support for new items added dynamically at order time
- PostgreSQL-backed relational schema for long-term data integrity

### 📊 Analytics Dashboard (Streamlit)
- Revenue, profit, and margin tracking
- Monthly KPIs and trends
- Item-level performance breakdowns
- Interactive charts (Altair)

### 🤖 AI Market Research Agents (CrewAI)
- Autonomous agents scan upcoming drops and releases
- Evaluate resale potential using:
  - Brand demand
  - Scarcity
  - Historical resale behavior
- Rank opportunities by expected ROI

---

## 🧱 Tech Stack

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

## 🗂️ Project Structure

```bash
flipper/
├── app.py                     # Main Streamlit entry point (Overview)
├── pages/                     # Streamlit multipage views
│   ├── inventory.py
│   ├── orders_and_expenses.py
│   └── sales.py
├── components/                # Reusable UI components
│   └── new_order_form.py
├── agents_notebook/           # CrewAI agents
│   └── market_research.py
├── sql/
│   └── schema.sql             # PostgreSQL schema
├── charts.py                  # Altair chart definitions
├── db.py                      # Database access layer
├── requirements.txt
└── README.md
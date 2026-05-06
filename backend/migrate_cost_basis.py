#!/usr/bin/env python3
"""
One-time migration: recalculate cost_basis, avg_cost_basis, and
unit_cost_basis_at_sale for all existing rows using the canonical WAC formula.

Run from the project root:
    python backend/migrate_cost_basis.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.db import recalculate_all_cost_basis

if __name__ == "__main__":
    print("Step 1/3  Recalculating order_items.cost_basis ...")
    print("Step 2/3  Recalculating items.avg_cost_basis (WAC) ...")
    print("Step 3/3  Recalculating sale_items.unit_cost_basis_at_sale (temporal WAC) ...")
    recalculate_all_cost_basis()
    print("Done. All cost basis values have been updated.")

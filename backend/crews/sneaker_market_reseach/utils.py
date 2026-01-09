import re
import unicodedata
from datetime import date, timedelta

def slugify(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    s = s.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s

def make_item_key(product_name: str, release_date: date, brand: str | None = None) -> str:
    parts = [slugify(product_name)]
    if brand:
        parts.insert(0, slugify(brand))
    parts.append(release_date.isoformat())
    return "_".join(parts)

def get_date_range():
    today = date.today()
    cutoff = today + timedelta(days=21)
    return today, cutoff
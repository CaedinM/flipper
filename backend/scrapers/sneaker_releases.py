"""
Sneaker release calendar scraper using RSS feeds.

Sources: sneakernews.com, sneakerbardetroit.com
"""

from __future__ import annotations

import re
import traceback
import unicodedata
from datetime import date, datetime

import feedparser
import pandas as pd

from backend.crews.db import (
    create_agent_run,
    generate_run_hash,
    get_existing_item_keys,
    insert_releases,
    update_agent_run,
)


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


def extract_price_from_text(text: str) -> int | None:
    """Find a dollar price in arbitrary text, e.g. '$180', 'priced at $220'."""
    match = re.search(r"\$\s*(\d{2,4})", text)
    if match:
        return int(match.group(1))
    return None


def parse_date_from_text(text: str) -> date | None:
    """Find and parse a date in arbitrary text."""
    if not text:
        return None

    month_names = (
        r"(?:January|February|March|April|May|June|July|August|"
        r"September|October|November|December|"
        r"Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\.?"
    )
    patterns = [
        (
            rf"\b({month_names}\s+\d{{1,2}},?\s+\d{{4}})\b",
            ["%B %d, %Y", "%B %d %Y", "%b %d, %Y", "%b %d %Y", "%b. %d, %Y", "%b. %d %Y"],
        ),
        (r"\b(\d{1,2}/\d{1,2}/\d{4})\b", ["%m/%d/%Y"]),
        (r"\b(\d{4}-\d{2}-\d{2})\b", ["%Y-%m-%d"]),
    ]

    for pattern, fmts in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            date_str = match.group(1).strip()
            for fmt in fmts:
                try:
                    return datetime.strptime(date_str, fmt).date()
                except ValueError:
                    continue

    return None


def clean_release_title(title: str) -> str | None:
    """Strip release/price boilerplate from an article title to get the product name."""
    cutoffs = [
        r"\s*[–\-|:]\s*release date.*",
        r"\s+release date.*",
        r"\s*[–\-|:]\s*price.*",
        r"\s+where to buy.*",
        r"\s*[–\-|:]\s*how to buy.*",
        r"\s*\|\s*.*$",
    ]
    cleaned = title
    for pattern in cutoffs:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE).strip()
    return cleaned if cleaned and len(cleaned) >= 8 else None


def extract_brand(product_name: str) -> str | None:
    name_lower = product_name.lower()
    brands = [
        ("Nike", ["nike", "air max", "air force", "dunk", "air jordan"]),
        ("Jordan", ["jordan", "aj1", "aj4", "aj11"]),
        ("Adidas", ["adidas", "yeezy", "ultra boost", "nmd"]),
        ("New Balance", ["new balance", "nb "]),
        ("Puma", ["puma"]),
        ("Reebok", ["reebok"]),
        ("Converse", ["converse", "chuck taylor"]),
        ("Vans", ["vans"]),
        ("Asics", ["asics", "gel-"]),
    ]
    for brand, keywords in brands:
        for keyword in keywords:
            if keyword in name_lower:
                return brand
    return None


SNEAKER_KEYWORDS = [
    "nike", "jordan", "air", "dunk", "force", "max",
    "adidas", "yeezy", "boost", "nmd", "superstar",
    "new balance", "puma", "reebok", "converse", "vans",
    "asics", "gel-", "saucony", "hoka",
    "retro", "og", "colorway", "low", "mid", "high",
    "sneaker", "shoe", "footwear", "kick",
    "sb", "se", "qs", "pe", "prm", "premium",
]


def is_valid_release(product_name: str) -> bool:
    if not product_name:
        return False
    name = product_name.strip()
    name_lower = name.lower()
    if len(name) < 8 or len(name) > 200:
        return False
    if not re.search(r"[a-zA-Z]{3,}", name):
        return False
    return any(kw in name_lower for kw in SNEAKER_KEYWORDS)


def _entry_image(entry) -> str | None:
    """Extract image URL from a feedparser entry."""
    for attr in ("media_content", "media_thumbnail"):
        items = getattr(entry, attr, None)
        if items and isinstance(items, list) and items[0].get("url"):
            return items[0]["url"]
    for enc in getattr(entry, "enclosures", []):
        if enc.get("type", "").startswith("image"):
            return enc.get("href") or enc.get("url")
    return None


def _scrape_rss(feed_url: str) -> list[dict]:
    """
    Generic RSS scraper for sneaker release feeds.
    Filters for articles that mention a future release date.
    """
    releases = []
    feed = feedparser.parse(feed_url)

    for entry in feed.entries:
        title = entry.get("title", "")
        summary = re.sub(r"<[^>]+>", " ", entry.get("summary", ""))
        combined = f"{title} {summary}"

        if "release" not in combined.lower():
            continue

        product_name = clean_release_title(title)
        if not product_name or not is_valid_release(product_name):
            continue

        release_date = parse_date_from_text(title) or parse_date_from_text(summary)
        if not release_date or release_date < date.today():
            continue

        releases.append({
            "product_name": product_name,
            "brand": extract_brand(product_name),
            "release_date": release_date,
            "retail_price": extract_price_from_text(combined),
            "source_url": entry.get("link", feed_url),
            "image_url": _entry_image(entry),
        })

    return releases


def scrape_sneakernews() -> list[dict]:
    return _scrape_rss("https://sneakernews.com/feed/")


def scrape_sneakerbardetroit() -> list[dict]:
    return _scrape_rss("https://sneakerbardetroit.com/feed/")


def run_release_scraper(num_items: int = 50) -> pd.DataFrame:
    inputs = {
        "num_items": num_items,
        "sources": ["sneakernews.com", "sneakerbardetroit.com"],
        "timestamp": datetime.now().isoformat(),
    }

    run_hash = generate_run_hash(inputs)
    crew_name = "sneaker_release_scraper"
    run_id = None

    try:
        run_id = create_agent_run(crew_name, inputs, run_hash)
        existing_keys = get_existing_item_keys()

        all_releases = []
        all_releases.extend(scrape_sneakernews())
        all_releases.extend(scrape_sneakerbardetroit())

        seen_keys: set[str] = set()
        unique_releases = []

        for release in all_releases:
            if not release.get("product_name") or not release.get("release_date"):
                continue

            item_key = make_item_key(
                product_name=release["product_name"],
                release_date=release["release_date"],
                brand=release.get("brand"),
            )

            if item_key in existing_keys or item_key in seen_keys:
                continue

            seen_keys.add(item_key)
            release["item_key"] = item_key
            unique_releases.append(release)

        unique_releases = unique_releases[:num_items]

        releases_data = [
            {
                "item_key": r["item_key"],
                "product_name": r["product_name"],
                "brand": r.get("brand"),
                "release_date": r["release_date"].isoformat(),
                "retail_price": r.get("retail_price"),
                "retailers": [],
                "seed_sources": [r.get("source_url", "")],
                "resale_estimate": None,
                "confidence_score": None,
                "image_url": r.get("image_url"),
            }
            for r in unique_releases
        ]

        if releases_data:
            insert_releases(run_id, releases_data)

        update_agent_run(
            run_id,
            status="succeeded",
            output={"releases_count": len(releases_data), "releases": releases_data},
        )

        return _releases_to_dataframe(releases_data)

    except Exception as e:
        if run_id:
            update_agent_run(run_id, status="failed", error=f"{e}\n\n{traceback.format_exc()}")
        raise


def _releases_to_dataframe(releases_data: list[dict]) -> pd.DataFrame:
    if not releases_data:
        return pd.DataFrame()
    return pd.DataFrame([
        {
            "Product Name": r.get("product_name", ""),
            "Brand": r.get("brand", "") or "",
            "Release Date": r.get("release_date"),
            "Retail Price": f"${r['retail_price']}" if r.get("retail_price") else "N/A",
        }
        for r in releases_data
    ])


if __name__ == "__main__":
    df = run_release_scraper()
    print(df)

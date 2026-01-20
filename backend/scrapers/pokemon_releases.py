"""
Deterministic Pokemon product release calendar scraper.

Scrapes release data from pokebeach.com and pokemoncenter.com.
"""

from __future__ import annotations

import re
import traceback
import unicodedata
from datetime import date, datetime
from urllib.parse import urljoin

import pandas as pd
import requests
from bs4 import BeautifulSoup

from backend.crews.db import (
    create_agent_run,
    generate_run_hash,
    get_existing_item_keys,
    insert_releases,
    update_agent_run,
)

# Request headers to mimic a browser
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}


def slugify(s: str) -> str:
    """Convert string to URL-safe slug."""
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    s = s.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s


def make_item_key(product_name: str, release_date: date, brand: str | None = None) -> str:
    """Generate a unique key for a release item."""
    parts = [slugify(product_name)]
    if brand:
        parts.insert(0, slugify(brand))
    parts.append(release_date.isoformat())
    return "_".join(parts)


def parse_price(price_str: str | None) -> int | None:
    """Parse price string like '$49.99' or '49.99' to integer."""
    if not price_str:
        return None
    # Extract digits and decimal
    match = re.search(r"[\d.]+", price_str)
    if match:
        try:
            return int(float(match.group()))
        except ValueError:
            return None
    return None


def parse_release_date(date_str: str) -> date | None:
    """Parse various date formats to a date object."""
    if not date_str:
        return None

    date_str = date_str.strip()

    # Remove ordinal suffixes (1st, 2nd, 3rd, 4th, etc.)
    date_str = re.sub(r"(\d+)(st|nd|rd|th)", r"\1", date_str)

    # Common date formats
    formats = [
        "%B %d, %Y",      # January 15, 2025
        "%b %d, %Y",      # Jan 15, 2025
        "%B %d %Y",       # January 15 2025 (no comma)
        "%b %d %Y",       # Jan 15 2025 (no comma)
        "%m/%d/%Y",       # 01/15/2025
        "%m-%d-%Y",       # 01-15-2025
        "%Y-%m-%d",       # 2025-01-15
        "%B %d",          # January 15 (current year)
        "%b %d",          # Jan 15 (current year)
        "%d %B %Y",       # 15 January 2025
        "%d %b %Y",       # 15 Jan 2025
    ]

    for fmt in formats:
        try:
            parsed = datetime.strptime(date_str, fmt)
            # If no year in format, use current or next year
            if "%Y" not in fmt:
                today = date.today()
                parsed = parsed.replace(year=today.year)
                # If date has passed, assume next year
                if parsed.date() < today:
                    parsed = parsed.replace(year=today.year + 1)
            return parsed.date()
        except ValueError:
            continue

    return None


def extract_product_type(product_name: str) -> str | None:
    """Extract product type from product name."""
    name_lower = product_name.lower()

    types = [
        ("TCG", ["booster", "elite trainer box", "etb", "collection box", "tin", "pack", "deck", "cards"]),
        ("Video Game", ["game", "scarlet", "violet", "legends", "switch"]),
        ("Plush", ["plush", "plushie", "stuffed"]),
        ("Figure", ["figure", "statue", "funko"]),
        ("Accessories", ["playmat", "sleeves", "binder", "case"]),
    ]

    for product_type, keywords in types:
        for keyword in keywords:
            if keyword in name_lower:
                return product_type

    return "Pokemon"


# Invalid patterns that indicate scraped garbage
INVALID_PATTERNS = [
    r"^#",
    r"^skip\s+to",
    r"^menu$",
    r"^search$",
    r"^home$",
    r"^logo$",
    r"^close$",
    r"^main-content",
    r"^navigation",
    r"^\d{1,2}[/-]\d{1,2}",
    r"^view\s+all",
    r"^see\s+more",
    r"^load\s+more",
    r"^read\s+more",
    r"^subscribe",
    r"^sign\s+up",
    r"^log\s*in",
    r"^cart$",
]

# Pokemon-related keywords that indicate a valid product
POKEMON_KEYWORDS = [
    "pokemon", "pikachu", "charizard", "mewtwo", "eevee",
    "booster", "elite trainer", "etb", "collection", "tin",
    "tcg", "trading card", "scarlet", "violet", "paldea",
    "plush", "figure", "playmat", "deck", "pack",
    "celebrations", "evolving", "obsidian", "temporal", "prismatic",
    "surging", "sparks", "evolutions", "paradox", "rift",
]


def is_valid_release(product_name: str) -> bool:
    """Check if a product name looks like a valid Pokemon release."""
    if not product_name:
        return False

    name = product_name.strip()
    name_lower = name.lower()

    if len(name) < 8 or len(name) > 200:
        return False

    for pattern in INVALID_PATTERNS:
        if re.match(pattern, name_lower):
            return False

    if not re.search(r"[a-zA-Z]{3,}", name):
        return False

    has_pokemon_keyword = any(kw in name_lower for kw in POKEMON_KEYWORDS)
    if not has_pokemon_keyword:
        return False

    return True


def extract_image_url(item, base_url: str) -> str | None:
    """Extract image URL from a release item element."""
    img_elem = item.select_one("img[src], img[data-src], img[data-lazy-src]")
    if img_elem:
        for attr in ["src", "data-src", "data-lazy-src", "data-original"]:
            img_url = img_elem.get(attr)
            if img_url and not img_url.startswith("data:"):
                if img_url.startswith("//"):
                    return "https:" + img_url
                elif img_url.startswith("/"):
                    return urljoin(base_url, img_url)
                elif img_url.startswith("http"):
                    return img_url
    return None


def scrape_serebii() -> list[dict]:
    """
    Scrape Pokemon TCG releases from serebii.net.

    Returns:
        List of release dicts with keys: product_name, brand, release_date,
        retail_price, source_url, image_url
    """
    releases = []
    url = "https://www.serebii.net/card/english.shtml"

    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "lxml")

        # Find the main table with set information
        tables = soup.select("table")
        if not tables:
            return releases

        # Parse table rows (skip header)
        rows = tables[0].select("tr")[1:]

        for row in rows:
            try:
                cells = row.select("td")
                if len(cells) < 5:
                    continue

                # Columns: Logo, Icon, Set Name, Number of Cards, Release Date
                set_name = cells[2].get_text(strip=True)
                release_date_str = cells[4].get_text(strip=True)

                if not set_name:
                    continue

                # Add "Pokemon TCG" prefix for clarity
                product_name = f"Pokemon TCG: {set_name}"

                release_date = parse_release_date(release_date_str)
                if not release_date:
                    continue

                # Extract image from logo cell
                img_elem = cells[0].select_one("img")
                image_url = None
                if img_elem:
                    img_src = img_elem.get("src")
                    if img_src:
                        image_url = urljoin(url, img_src)

                # Extract link to set page
                link_elem = cells[2].select_one("a")
                source_url = url
                if link_elem:
                    href = link_elem.get("href")
                    if href:
                        source_url = urljoin("https://www.serebii.net", href)

                releases.append({
                    "product_name": product_name,
                    "brand": "TCG",
                    "release_date": release_date,
                    "retail_price": None,
                    "source_url": source_url,
                    "image_url": image_url,
                })

            except Exception:
                continue

    except requests.RequestException:
        pass

    return releases


def scrape_pokemon_center() -> list[dict]:
    """
    Scrape Pokemon releases from pokemoncenter.com new arrivals.

    Returns:
        List of release dicts with keys: product_name, brand, release_date,
        retail_price, source_url, image_url
    """
    releases = []
    url = "https://www.pokemoncenter.com/en-us/category/new-arrivals"

    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "lxml")

        # Look for product cards
        release_items = soup.select(".product-card, .product-tile, [class*='product']")

        if not release_items:
            release_items = soup.select("article, .item, li[class*='product']")

        for item in release_items:
            try:
                name_elem = item.select_one("h2, h3, h4, .product-name, .title, a[title]")
                if not name_elem:
                    continue

                product_name = name_elem.get_text(strip=True) or name_elem.get("title", "")

                if not is_valid_release(product_name):
                    continue

                # Pokemon Center usually shows current availability, not future dates
                # Use today's date as a placeholder for new arrivals
                release_date = date.today()

                price_elem = item.select_one(".price, [class*='price']")
                price_str = price_elem.get_text(strip=True) if price_elem else None
                retail_price = parse_price(price_str)

                link_elem = item.select_one("a[href]")
                source_url = link_elem.get("href") if link_elem else url
                if source_url and not source_url.startswith("http"):
                    source_url = urljoin(url, source_url)

                image_url = extract_image_url(item, url)

                product_type = extract_product_type(product_name)

                releases.append({
                    "product_name": product_name,
                    "brand": product_type,
                    "release_date": release_date,
                    "retail_price": retail_price,
                    "source_url": source_url,
                    "image_url": image_url,
                })

            except Exception:
                continue

    except requests.RequestException:
        pass

    return releases


def run_release_scraper(num_items: int = 10) -> pd.DataFrame:
    """
    Run the Pokemon release scraper and save results to database.

    Args:
        num_items: Maximum number of releases to return (default 10)

    Returns:
        DataFrame with the release data
    """
    inputs = {
        "num_items": num_items,
        "sources": ["serebii.net", "pokemoncenter.com"],
        "timestamp": datetime.now().isoformat(),
        "category": "pokemon",
    }

    run_hash = generate_run_hash(inputs)
    crew_name = "pokemon_release_scraper"
    run_id = None

    try:
        run_id = create_agent_run(crew_name, inputs, run_hash)

        existing_keys = get_existing_item_keys()

        all_releases = []
        all_releases.extend(scrape_serebii())
        all_releases.extend(scrape_pokemon_center())

        seen_keys = set()
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

        releases_data = []
        for release in unique_releases:
            releases_data.append({
                "item_key": release["item_key"],
                "product_name": release["product_name"],
                "brand": release.get("brand"),
                "release_date": release["release_date"].isoformat(),
                "retail_price": release.get("retail_price"),
                "retailers": [],
                "seed_sources": [release.get("source_url", "")],
                "resale_estimate": None,
                "confidence_score": None,
                "image_url": release.get("image_url"),
            })

        if releases_data:
            insert_releases(run_id, releases_data)

        output_data = {
            "releases_count": len(releases_data),
            "releases": releases_data,
        }

        update_agent_run(run_id, status="succeeded", output=output_data)

        return _releases_to_dataframe(releases_data)

    except Exception as e:
        error_message = str(e)
        error_traceback = traceback.format_exc()
        full_error = f"{error_message}\n\n{error_traceback}"

        if run_id:
            update_agent_run(run_id, status="failed", error=full_error)

        raise


def _releases_to_dataframe(releases_data: list[dict]) -> pd.DataFrame:
    """Convert releases data to a formatted DataFrame for display."""
    if not releases_data:
        return pd.DataFrame()

    rows = []
    for item in releases_data:
        seed_sources = item.get("seed_sources") or []
        seed_sources_str = ", ".join(seed_sources) if isinstance(seed_sources, list) else str(seed_sources)

        row = {
            "Product Name": item.get("product_name", ""),
            "Type": item.get("brand", "") or "",
            "Release Date": item.get("release_date"),
            "Retail Price": f"${item['retail_price']}" if item.get("retail_price") else "N/A",
            "Sources": seed_sources_str,
        }
        rows.append(row)

    return pd.DataFrame(rows)


if __name__ == "__main__":
    df = run_release_scraper(num_items=10)
    print(df)

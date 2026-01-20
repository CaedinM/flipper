"""
Deterministic sneaker release calendar scraper.

Scrapes release data from sneakernews.com and nicekicks.com.
"""

from __future__ import annotations

import re
import traceback
import unicodedata
from datetime import date, datetime

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
    """Parse price string like '$180' or '180' to integer."""
    if not price_str:
        return None
    # Remove non-numeric characters except digits
    digits = re.sub(r"[^\d]", "", price_str)
    return int(digits) if digits else None


def parse_release_date(date_str: str) -> date | None:
    """Parse various date formats to a date object."""
    if not date_str:
        return None

    date_str = date_str.strip()

    # Common date formats
    formats = [
        "%B %d, %Y",      # January 15, 2025
        "%b %d, %Y",      # Jan 15, 2025
        "%m/%d/%Y",       # 01/15/2025
        "%m-%d-%Y",       # 01-15-2025
        "%Y-%m-%d",       # 2025-01-15
        "%B %d",          # January 15 (current year)
        "%b %d",          # Jan 15 (current year)
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


def extract_brand(product_name: str) -> str | None:
    """Extract brand from product name."""
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


# Invalid patterns that indicate scraped garbage, not actual products
INVALID_PATTERNS = [
    r"^#",                          # Starts with hash (anchor links)
    r"^skip\s+to",                  # Skip to content links
    r"^menu$",                      # Navigation menu
    r"^search$",                    # Search buttons
    r"^home$",                      # Home links
    r"^logo$",                      # Logo elements
    r"^close$",                     # Close buttons
    r"^main-content",               # Main content anchors
    r"^navigation",                 # Navigation elements
    r"^\d{1,2}[/-]\d{1,2}",         # Starts with date pattern
    r"^(january|february|march|april|may|june|july|august|september|october|november|december)\s+\d",  # Month + day
    r"^(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\s+\d",  # Abbreviated month + day
    r"^\d{4}$",                     # Just a year
    r"^view\s+all",                 # View all links
    r"^see\s+more",                 # See more links
    r"^load\s+more",                # Load more buttons
    r"^read\s+more",                # Read more links
    r"^click\s+here",               # Click here links
    r"^subscribe",                  # Subscribe buttons
    r"^sign\s+up",                  # Sign up links
    r"^log\s*in",                   # Login links
    r"^cart$",                      # Cart links
    r"^checkout$",                  # Checkout links
]

# Sneaker-related keywords that indicate a valid product
SNEAKER_KEYWORDS = [
    "nike", "jordan", "air", "dunk", "force", "max",
    "adidas", "yeezy", "boost", "nmd", "superstar",
    "new balance", "puma", "reebok", "converse", "vans",
    "asics", "gel", "saucony", "brooks", "hoka",
    "retro", "og", "colorway", "low", "mid", "high",
    "sneaker", "shoe", "footwear", "kick",
    "sb", "se", "qs", "pe", "prm", "premium",
]


def is_valid_release(product_name: str) -> bool:
    """
    Check if a product name looks like a valid sneaker release.

    Filters out navigation elements, dates, and other garbage data.
    """
    if not product_name:
        return False

    name = product_name.strip()
    name_lower = name.lower()

    # Must be reasonable length (not too short, not too long)
    if len(name) < 10 or len(name) > 200:
        return False

    # Check against invalid patterns
    for pattern in INVALID_PATTERNS:
        if re.match(pattern, name_lower):
            return False

    # Must contain at least some letters (not just numbers/symbols)
    if not re.search(r"[a-zA-Z]{3,}", name):
        return False

    # Should contain at least one sneaker-related keyword
    has_sneaker_keyword = any(kw in name_lower for kw in SNEAKER_KEYWORDS)
    if not has_sneaker_keyword:
        return False

    # Reject if it looks like a date string only
    if re.match(r"^[A-Za-z]+\s+\d{1,2},?\s*\d{0,4}$", name):
        return False

    return True


def extract_image_url(item, base_url: str) -> str | None:
    """Extract image URL from a release item element."""
    # Try various image selectors
    img_elem = item.select_one("img[src], img[data-src], img[data-lazy-src]")
    if img_elem:
        # Try different attributes where the image URL might be stored
        for attr in ["src", "data-src", "data-lazy-src", "data-original"]:
            img_url = img_elem.get(attr)
            if img_url and not img_url.startswith("data:"):
                # Make absolute URL if relative
                if img_url.startswith("//"):
                    return "https:" + img_url
                elif img_url.startswith("/"):
                    from urllib.parse import urljoin
                    return urljoin(base_url, img_url)
                elif img_url.startswith("http"):
                    return img_url
    return None


def scrape_sneakernews() -> list[dict]:
    """
    Scrape sneaker releases from sneakernews.com/release-dates/.

    Returns:
        List of release dicts with keys: product_name, brand, release_date,
        retail_price, source_url, image_url
    """
    releases = []
    url = "https://sneakernews.com/release-dates/"

    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "lxml")

        # Find release items - sneakernews uses article elements with release data
        release_items = soup.select("article.release-date-item, .release-date-entry, .rd-item")

        # Fallback: look for common release item patterns
        if not release_items:
            release_items = soup.select("[class*='release'], [class*='sneaker']")

        for item in release_items:
            try:
                # Try to extract product name
                name_elem = item.select_one("h2, h3, .title, .name, a[title]")
                if not name_elem:
                    continue

                product_name = name_elem.get_text(strip=True) or name_elem.get("title", "")

                # Validate the product name
                if not is_valid_release(product_name):
                    continue

                # Extract date
                date_elem = item.select_one(".date, .release-date, time, [class*='date']")
                date_str = date_elem.get_text(strip=True) if date_elem else None
                release_date = parse_release_date(date_str) if date_str else None

                # Extract price
                price_elem = item.select_one(".price, [class*='price']")
                price_str = price_elem.get_text(strip=True) if price_elem else None
                retail_price = parse_price(price_str)

                # Extract link
                link_elem = item.select_one("a[href]")
                source_url = link_elem.get("href") if link_elem else url

                # Extract image
                image_url = extract_image_url(item, url)

                # Extract brand
                brand = extract_brand(product_name)

                releases.append({
                    "product_name": product_name,
                    "brand": brand,
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


def scrape_nicekicks() -> list[dict]:
    """
    Scrape sneaker releases from nicekicks.com/release-dates/.

    Returns:
        List of release dicts with keys: product_name, brand, release_date,
        retail_price, source_url, image_url
    """
    releases = []
    url = "https://nicekicks.com/release-dates/"

    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "lxml")

        # NiceKicks uses various selectors for releases
        release_items = soup.select(".release-date-item, .release-entry, article.release")

        # Fallback: look for common patterns
        if not release_items:
            release_items = soup.select("[class*='release'], .sneaker-item, article")

        for item in release_items:
            try:
                # Try to extract product name
                name_elem = item.select_one("h2, h3, h4, .title, .name, a[title]")
                if not name_elem:
                    continue

                product_name = name_elem.get_text(strip=True) or name_elem.get("title", "")

                # Validate the product name
                if not is_valid_release(product_name):
                    continue

                # Extract date
                date_elem = item.select_one(".date, .release-date, time, [class*='date']")
                date_str = date_elem.get_text(strip=True) if date_elem else None
                release_date = parse_release_date(date_str) if date_str else None

                # Extract price
                price_elem = item.select_one(".price, [class*='price']")
                price_str = price_elem.get_text(strip=True) if price_elem else None
                retail_price = parse_price(price_str)

                # Extract link
                link_elem = item.select_one("a[href]")
                source_url = link_elem.get("href") if link_elem else url

                # Extract image
                image_url = extract_image_url(item, url)

                # Extract brand
                brand = extract_brand(product_name)

                releases.append({
                    "product_name": product_name,
                    "brand": brand,
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
    Run the sneaker release scraper and save results to database.

    Args:
        num_items: Maximum number of releases to return (default 10)

    Returns:
        DataFrame with the release data
    """
    inputs = {
        "num_items": num_items,
        "sources": ["sneakernews.com", "nicekicks.com"],
        "timestamp": datetime.now().isoformat(),
    }

    run_hash = generate_run_hash(inputs)
    crew_name = "sneaker_release_scraper"
    run_id = None

    try:
        # Create agent run with 'running' status
        run_id = create_agent_run(crew_name, inputs, run_hash)

        # Get existing item keys from database to avoid duplicates
        existing_keys = get_existing_item_keys()

        # Scrape from both sources
        all_releases = []
        all_releases.extend(scrape_sneakernews())
        all_releases.extend(scrape_nicekicks())

        # Deduplicate by item_key and filter out existing releases
        seen_keys = set()
        unique_releases = []

        for release in all_releases:
            # Skip releases without required data
            if not release.get("product_name") or not release.get("release_date"):
                continue

            item_key = make_item_key(
                product_name=release["product_name"],
                release_date=release["release_date"],
                brand=release.get("brand"),
            )

            # Skip if already in database or already seen in this batch
            if item_key in existing_keys or item_key in seen_keys:
                continue

            seen_keys.add(item_key)
            release["item_key"] = item_key
            unique_releases.append(release)

        # Limit to requested number
        unique_releases = unique_releases[:num_items]

        # Prepare releases for database insertion
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

        # Insert releases into database
        if releases_data:
            insert_releases(run_id, releases_data)

        # Prepare output for agent_runs table
        output_data = {
            "releases_count": len(releases_data),
            "releases": releases_data,
        }

        # Update agent run with success status
        update_agent_run(run_id, status="succeeded", output=output_data)

        # Convert to DataFrame for display
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
        retailers = item.get("retailers") or []
        retailers_str = ", ".join(retailers) if isinstance(retailers, list) else str(retailers)

        seed_sources = item.get("seed_sources") or []
        seed_sources_str = ", ".join(seed_sources) if isinstance(seed_sources, list) else str(seed_sources)

        row = {
            "Product Name": item.get("product_name", ""),
            "Brand": item.get("brand", "") or "",
            "Release Date": item.get("release_date"),
            "Retail Price": f"${item['retail_price']}" if item.get("retail_price") else "N/A",
            "Resale Estimate": "N/A",
            "Confidence": "N/A",
            "Retailers": retailers_str,
            "Sources": seed_sources_str,
        }
        rows.append(row)

    return pd.DataFrame(rows)


if __name__ == "__main__":
    df = run_release_scraper(num_items=10)
    print(df)

import streamlit as st
import sys
from pathlib import Path
from datetime import date

# Add project root to path for backend imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from frontend.state import init_state
from backend.db import run_query_df

if "refresh_token" not in st.session_state:
    init_state()

st.set_page_config(page_title="Sneaker Calendar", layout="wide")
st.title("Sneaker Release Calendar")
st.caption("Upcoming sneaker releases")


def get_upcoming_releases(refresh_token: int):
    return run_query_df("""
        SELECT DISTINCT ON (r.item_key)
            r.product_name,
            r.brand,
            r.release_date,
            r.retail_price,
            r.image_url
        FROM releases r
        JOIN agent_runs ar ON r.run_id = ar.id
        WHERE ar.status = 'succeeded'
          AND ar.crew_name = 'sneaker_release_scraper'
          AND r.release_date >= CURRENT_DATE
        ORDER BY r.item_key, ar.start_time DESC
    """, refresh_token)


releases_df = get_upcoming_releases(st.session_state.refresh_token)

if not releases_df.empty:
    # Summary metrics
    st.metric("Upcoming Releases", len(releases_df))

    st.divider()

    # Group releases by date
    releases_df = releases_df.sort_values("release_date")

    for release_date in releases_df["release_date"].unique():
        date_releases = releases_df[releases_df["release_date"] == release_date]

        # Format date header
        if hasattr(release_date, "strftime"):
            date_str = release_date.strftime("%A, %B %d, %Y")
        else:
            date_str = str(release_date)

        st.subheader(date_str)

        # Display releases in a grid layout
        cols = st.columns(3)
        for idx, (_, release) in enumerate(date_releases.iterrows()):
            with cols[idx % 3]:
                with st.container(border=True):
                    # Display image if available
                    image_url = release["image_url"]
                    if image_url and str(image_url) != "nan":
                        try:
                            st.image(image_url, use_container_width=True)
                        except Exception:
                            pass

                    st.markdown(f"**{release['product_name']}**")

                    col_brand, col_price = st.columns(2)
                    with col_brand:
                        if release["brand"]:
                            st.caption(release["brand"])
                    with col_price:
                        price = release["retail_price"]
                        st.caption(f"${int(price)}" if price else "TBD")

        st.divider()
else:
    st.info("No upcoming releases found.")

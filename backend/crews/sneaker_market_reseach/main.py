from __future__ import annotations
from .crew import sneaker_research_crew
from .utils import get_date_range, make_item_key
from ..db import create_agent_run, update_agent_run, insert_releases, generate_run_hash
import traceback
import pandas as pd


def run_market_research(num_items: int = 3) -> pd.DataFrame:
    """
    Run the sneaker market research crew and save results to database.

    Args:
        num_items: Number of releases to find (default 3)

    Returns:
        DataFrame with the release data
    """
    today, cutoff = get_date_range()

    # Prepare inputs
    inputs = {
        "today": today.isoformat(),
        "cutoff_date": cutoff.isoformat(),
        "num_items": num_items
    }

    # Generate run hash and create agent run record
    run_hash = generate_run_hash(inputs)
    crew_name = "sneaker_market_research"
    run_id = None

    try:
        # Create agent run with 'running' status
        run_id = create_agent_run(crew_name, inputs, run_hash)

        # Execute the crew
        result = sneaker_research_crew.kickoff(inputs=inputs)

        # Process the result and extract releases
        releases_data = []
        # Access the final pydantic output (AnalystOutput)
        analyst_output = result.pydantic if hasattr(result, 'pydantic') else None

        # Fallback: try to get from tasks_output if pydantic is not available
        if not analyst_output and hasattr(result, 'raw') and hasattr(result.raw, 'tasks_output'):
            if result.raw.tasks_output:
                last_task = result.raw.tasks_output[-1]
                analyst_output = last_task.pydantic if hasattr(last_task, 'pydantic') else None

        if analyst_output and hasattr(analyst_output, 'items'):
            for item in analyst_output.items:
                item_key = make_item_key(
                    product_name=item.product_name,
                    release_date=item.release_date,
                    brand=item.brand
                )

                # Convert retailers to list if it's a string
                retailers_list = item.retailers
                if isinstance(retailers_list, str):
                    retailers_list = [retailers_list] if retailers_list else []
                elif retailers_list is None:
                    retailers_list = []

                release_dict = {
                    "item_key": item_key,
                    "product_name": item.product_name,
                    "brand": item.brand,
                    "release_date": item.release_date.isoformat() if hasattr(item.release_date, 'isoformat') else str(item.release_date),
                    "retail_price": item.retail_price,
                    "retailers": retailers_list,
                    "seed_sources": item.seed_sources or [],
                    "resale_estimate": item.resale_estimate,
                    "confidence_score": int(item.confidence_score)
                }
                releases_data.append(release_dict)

        # Insert releases into database
        if releases_data:
            insert_releases(run_id, releases_data)

        # Capture usage metrics from the crew
        usage_metrics = {}
        if hasattr(sneaker_research_crew, 'usage_metrics') and sneaker_research_crew.usage_metrics:
            metrics = sneaker_research_crew.usage_metrics
            usage_metrics = {
                "total_tokens": getattr(metrics, 'total_tokens', 0),
                "prompt_tokens": getattr(metrics, 'prompt_tokens', 0),
                "completion_tokens": getattr(metrics, 'completion_tokens', 0),
                "cached_prompt_tokens": getattr(metrics, 'cached_prompt_tokens', 0),
                "successful_requests": getattr(metrics, 'successful_requests', 0),
            }
            # Calculate estimated cost (gpt-4o-mini pricing: $0.15 per 1M tokens)
            total_tokens = usage_metrics["prompt_tokens"] + usage_metrics["completion_tokens"]
            usage_metrics["estimated_cost_usd"] = round(0.150 * total_tokens / 1_000_000, 4)

        # Prepare output for agent_runs table
        output_data = {
            "releases_count": len(releases_data),
            "releases": releases_data,
            "usage_metrics": usage_metrics
        }

        # Update agent run with success status
        update_agent_run(run_id, status="succeeded", output=output_data)

        # Convert to DataFrame for display
        return _releases_to_dataframe(releases_data)

    except Exception as e:
        # Update agent run with failure status
        error_message = str(e)
        error_traceback = traceback.format_exc()
        full_error = f"{error_message}\n\n{error_traceback}"

        if run_id:
            update_agent_run(run_id, status="failed", error=full_error)

        # Re-raise the exception
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
            "Resale Estimate": f"${item['resale_estimate']}" if item.get("resale_estimate") else "N/A",
            "Confidence": f"{item['confidence_score']}%" if item.get("confidence_score") is not None else "N/A",
            "Retailers": retailers_str,
            "Sources": seed_sources_str
        }
        rows.append(row)

    return pd.DataFrame(rows)


if __name__ == "__main__":
    # Run as script with default settings
    df = run_market_research(num_items=3)
    print(df)

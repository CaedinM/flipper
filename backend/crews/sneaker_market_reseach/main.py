from __future__ import annotations
from .crew import sneaker_research_crew
from .utils import get_date_range, make_item_key
from ..db import create_agent_run, update_agent_run, insert_releases, generate_run_hash
import traceback

# Change number of items
num_items = 2

today, cutoff = get_date_range()

if __name__ == "__main__":
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
        print(f"Created agent run with ID: {run_id}")
        
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
                    "release_date": item.release_date,
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
            print(f"Inserted {len(releases_data)} releases into database")
        
        # Prepare output for agent_runs table
        output_data = {
            "releases_count": len(releases_data),
            "releases": releases_data
        }
        
        # Update agent run with success status
        update_agent_run(run_id, status="succeeded", output=output_data)
        print(f"Agent run {run_id} completed successfully")
        
    except Exception as e:
        # Update agent run with failure status
        error_message = str(e)
        error_traceback = traceback.format_exc()
        full_error = f"{error_message}\n\n{error_traceback}"
        
        if run_id:
            update_agent_run(run_id, status="failed", error=full_error)
            print(f"Agent run {run_id} failed: {error_message}")
        else:
            print(f"Failed to create agent run: {error_message}")
        
        # Re-raise the exception so it's visible
        raise
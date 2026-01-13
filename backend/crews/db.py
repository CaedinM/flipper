import os
import psycopg2
import hashlib
import json
from psycopg2.extras import RealDictCursor, execute_values
from dotenv import load_dotenv
from pathlib import Path

# Load .env.local from project root
project_root = Path(__file__).parent.parent.parent
env_path = project_root / ".env.local"
load_dotenv(str(env_path), override=True)

def get_dict_connection():
    """Get a database connection with RealDictCursor."""
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        cursor_factory=RealDictCursor,
    )

def generate_run_hash(inputs: dict) -> str:
    """Generate a unique hash for a run based on inputs."""
    # Sort inputs to ensure consistent hashing
    sorted_inputs = json.dumps(inputs, sort_keys=True)
    return hashlib.sha256(sorted_inputs.encode()).hexdigest()

def create_agent_run(crew_name: str, inputs: dict, run_hash: str) -> int:
    """
    Create a new agent run record.
    Returns the run_id.
    """
    with get_dict_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO agent_runs (crew_name, status, input, run_hash)
                VALUES (%s, 'running', %s, %s)
                RETURNING id
                """,
                (crew_name, json.dumps(inputs), run_hash)
            )
            result = cur.fetchone()
            return result["id"]

def update_agent_run(run_id: int, status: str, output: dict | None = None, error: str | None = None):
    """
    Update an agent run with finish time, status, output, and/or error.
    Status must be 'succeeded' or 'failed'.
    """
    with get_dict_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE agent_runs
                SET finish_time = NOW(),
                    status = %s,
                    output = COALESCE(%s, output),
                    error = COALESCE(%s, error)
                WHERE id = %s
                """,
                (
                    status,
                    json.dumps(output) if output else None,
                    error,
                    run_id
                )
            )

def insert_releases(run_id: int, releases: list[dict]):
    """
    Insert release records linked to an agent run.
    
    Args:
        run_id: The agent run ID
        releases: List of dicts with keys:
            - item_key: str
            - product_name: str
            - brand: str | None
            - release_date: date
            - retail_price: int | None
            - retailers: list[str] | None
            - seed_sources: list[str] | None
            - resale_estimate: int
            - confidence_score: int (0-100)
    """
    with get_dict_connection() as conn:
        with conn.cursor() as cur:
            values = [
                (
                    run_id,
                    r["item_key"],
                    r.get("product_name"),
                    r.get("brand"),
                    r.get("release_date"),
                    r.get("retail_price"),
                    r.get("retailers") or [],
                    r.get("seed_sources") or [],
                    r.get("resale_estimate"),
                    r.get("confidence_score")
                )
                for r in releases
            ]
            
            execute_values(
                cur,
                """
                INSERT INTO releases (
                    run_id, item_key, product_name, brand, release_date,
                    retail_price, retailers, seed_sources, resale_estimate, confidence_score
                )
                VALUES %s
                ON CONFLICT (run_id, item_key) DO UPDATE SET
                    product_name = EXCLUDED.product_name,
                    brand = EXCLUDED.brand,
                    release_date = EXCLUDED.release_date,
                    retail_price = EXCLUDED.retail_price,
                    retailers = EXCLUDED.retailers,
                    seed_sources = EXCLUDED.seed_sources,
                    resale_estimate = EXCLUDED.resale_estimate,
                    confidence_score = EXCLUDED.confidence_score
                """,
                values,
            )

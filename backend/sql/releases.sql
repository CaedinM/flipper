CREATE TABLE IF NOT EXISTS agent_runs (
    id SERIAL PRIMARY KEY,
    crew_name TEXT NOT NULL,
    start_time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finish_time TIMESTAMPTZ,
    status TEXT NOT NULL CHECK (status IN ('running','succeeded','failed')),
    input JSONB,
    output JSONB,
    error TEXT,
    run_hash TEXT unique
);

CREATE TABLE IF NOT EXISTS releases (
    id SERIAL PRIMARY KEY,
    run_id INT REFERENCES agent_runs(id) ON DELETE CASCADE,
    item_key TEXT NOT NULL,
    product_name TEXT,
    brand TEXT,
    release_date DATE,
    retail_price INT,
    retailers TEXT[],
    seed_sources TEXT[],
    resale_estimate INT,
    confidence_score INT CHECK (confidence_score >= 0 AND confidence_score <= 100),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    UNIQUE (run_id, item_key)  
);

CREATE INDEX IF NOT EXISTS idx_releases_run_id ON releases(run_id);
CREATE INDEX IF NOT EXISTS idx_releases_item_key ON releases(item_key);
CREATE INDEX IF NOT EXISTS idx_releases_release_date ON releases(release_date);
ALTER TABLE bulk_evaluation_results
    ADD COLUMN IF NOT EXISTS run_id TEXT,
    ADD COLUMN IF NOT EXISTS destination_set_id TEXT,
    ADD COLUMN IF NOT EXISTS origin_key TEXT,
    ADD COLUMN IF NOT EXISTS origin_lat DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS origin_lon DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS origin_uf TEXT,
    ADD COLUMN IF NOT EXISTS destiny_key TEXT,
    ADD COLUMN IF NOT EXISTS destiny_lat DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS destiny_lon DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS destiny_uf TEXT,
    ADD COLUMN IF NOT EXISTS port_origin_name TEXT,
    ADD COLUMN IF NOT EXISTS port_destiny_name TEXT,
    ADD COLUMN IF NOT EXISTS emissions_savings_pct DOUBLE PRECISION;

UPDATE bulk_evaluation_results
   SET origin_key = COALESCE(NULLIF(origin_key, ''), LOWER(TRIM(origin_name))),
       destiny_key = COALESCE(NULLIF(destiny_key, ''), LOWER(TRIM(destiny_name)))
 WHERE TRIM(COALESCE(origin_name, '')) <> ''
   AND TRIM(COALESCE(destiny_name, '')) <> ''
   AND (
        TRIM(COALESCE(origin_key, '')) = ''
        OR TRIM(COALESCE(destiny_key, '')) = ''
   );

CREATE INDEX IF NOT EXISTS idx_bulk_evaluation_results_run_id
    ON bulk_evaluation_results (run_id);

CREATE INDEX IF NOT EXISTS idx_bulk_evaluation_results_origin_cargo_status
    ON bulk_evaluation_results (origin_key, cargo_t, status);

CREATE TABLE IF NOT EXISTS bulk_evaluation_runs (
      run_id                    TEXT PRIMARY KEY
    , origin_key                TEXT      NOT NULL
    , origin_name               TEXT      NOT NULL
    , input_origin              TEXT      NOT NULL
    , cargo_t                   DOUBLE PRECISION NOT NULL
    , truck_key                 TEXT      NOT NULL
    , ors_profile               TEXT      NOT NULL
    , vessel_class              TEXT
    , include_hoteling          INTEGER   NOT NULL DEFAULT 1
    , hoteling_hours_per_call   DOUBLE PRECISION
    , port_calls                INTEGER
    , include_port_ops          INTEGER   NOT NULL DEFAULT 1
    , port_moves_per_call       DOUBLE PRECISION
    , cargo_teu                 DOUBLE PRECISION
    , t_per_teu_default         DOUBLE PRECISION
    , allocation_mode           TEXT
    , allocation_load_factor    DOUBLE PRECISION
    , full_call_mode            INTEGER   NOT NULL DEFAULT 0
    , port_ops_scenario         TEXT
    , destination_set_id        TEXT      NOT NULL
    , destination_count         INTEGER   NOT NULL DEFAULT 0
    , success_count             INTEGER   NOT NULL DEFAULT 0
    , fail_count                INTEGER   NOT NULL DEFAULT 0
    , status                    TEXT      NOT NULL
    , error_message             TEXT
    , duration_s                DOUBLE PRECISION
    , started_timestamp         TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
    , completed_timestamp       TIMESTAMPTZ
    , updated_timestamp         TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_bulk_evaluation_runs_selector
    ON bulk_evaluation_runs (origin_key, cargo_t, destination_set_id, status, updated_timestamp);

CREATE INDEX IF NOT EXISTS idx_bulk_evaluation_runs_status
    ON bulk_evaluation_runs (status);

CREATE TABLE IF NOT EXISTS bulk_evaluation_run_results (
      run_id                    TEXT      NOT NULL
    , scenario_key              TEXT      NOT NULL
    , origin_key                TEXT      NOT NULL
    , origin_name               TEXT      NOT NULL
    , origin_lat                DOUBLE PRECISION
    , origin_lon                DOUBLE PRECISION
    , origin_uf                 TEXT
    , destiny_key               TEXT      NOT NULL
    , destiny_name              TEXT      NOT NULL
    , destiny_lat               DOUBLE PRECISION
    , destiny_lon               DOUBLE PRECISION
    , destiny_uf                TEXT
    , input_origin              TEXT      NOT NULL
    , input_destiny             TEXT      NOT NULL
    , destination_set_id        TEXT      NOT NULL
    , port_origin_name          TEXT
    , port_destiny_name         TEXT
    , status                    TEXT      NOT NULL
    , error_message             TEXT
    , road_cost_r               DOUBLE PRECISION
    , multimodal_cost_r         DOUBLE PRECISION
    , cost_delta_r              DOUBLE PRECISION
    , cost_savings_pct          DOUBLE PRECISION
    , road_emissions_kg         DOUBLE PRECISION
    , multimodal_emissions_kg   DOUBLE PRECISION
    , emissions_delta_kg        DOUBLE PRECISION
    , emissions_savings_pct     DOUBLE PRECISION
    , road_distance_km          DOUBLE PRECISION
    , sea_km                    DOUBLE PRECISION
    , insertion_timestamp       TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
    , updated_timestamp         TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
    , PRIMARY KEY (run_id, scenario_key)
);

CREATE INDEX IF NOT EXISTS idx_bulk_evaluation_run_results_run_status
    ON bulk_evaluation_run_results (run_id, status);

CREATE INDEX IF NOT EXISTS idx_bulk_evaluation_run_results_coords
    ON bulk_evaluation_run_results (run_id, destiny_lat, destiny_lon);

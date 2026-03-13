CREATE TABLE IF NOT EXISTS locations (
      id                  BIGSERIAL PRIMARY KEY
    , lat6                NUMERIC(9, 6) NOT NULL
    , lon6                NUMERIC(9, 6) NOT NULL
    , label               TEXT
    , street              TEXT
    , house_number        TEXT
    , neighborhood        TEXT
    , city                TEXT
    , state               TEXT
    , postal_code         TEXT
    , provider            TEXT
    , provider_payload    JSONB
    , insertion_timestamp TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
    , updated_timestamp   TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
    , CONSTRAINT ck_locations_lat6 CHECK (lat6 BETWEEN -90.000000 AND 90.000000)
    , CONSTRAINT ck_locations_lon6 CHECK (lon6 BETWEEN -180.000000 AND 180.000000)
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_locations_lat_lon
    ON locations (lat6, lon6);

CREATE INDEX IF NOT EXISTS idx_locations_updated_timestamp
    ON locations (updated_timestamp DESC);

CREATE TABLE IF NOT EXISTS location_aliases (
      place_key           TEXT PRIMARY KEY
    , alias_label         TEXT      NOT NULL
    , location_id         BIGINT    NOT NULL REFERENCES locations(id) ON DELETE CASCADE
    , provider            TEXT
    , source              TEXT      NOT NULL DEFAULT 'geocode'
    , insertion_timestamp TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
    , updated_timestamp   TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_location_aliases_location_id
    ON location_aliases (location_id);

CREATE INDEX IF NOT EXISTS idx_location_aliases_updated_timestamp
    ON location_aliases (updated_timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_location_aliases_alias_label
    ON location_aliases (alias_label);

CREATE TABLE IF NOT EXISTS route_cache_entries (
      id                  BIGSERIAL PRIMARY KEY
    , origin_location_id  BIGINT    NOT NULL REFERENCES locations(id) ON DELETE CASCADE
    , destiny_location_id BIGINT    NOT NULL REFERENCES locations(id) ON DELETE CASCADE
    , is_hgv              BOOLEAN   NOT NULL DEFAULT TRUE
    , fallback_profile    TEXT
    , provider            TEXT      NOT NULL DEFAULT 'ors'
    , distance_km         DOUBLE PRECISION
    , duration_s          DOUBLE PRECISION
    , insertion_timestamp TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
    , updated_timestamp   TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_route_cache_entries_origin_destiny_mode
    ON route_cache_entries (origin_location_id, destiny_location_id, is_hgv);

CREATE INDEX IF NOT EXISTS idx_route_cache_entries_updated_timestamp
    ON route_cache_entries (updated_timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_route_cache_entries_origin_location
    ON route_cache_entries (origin_location_id);

CREATE INDEX IF NOT EXISTS idx_route_cache_entries_destiny_location
    ON route_cache_entries (destiny_location_id);

CREATE TABLE IF NOT EXISTS bulk_runs (
      run_id                    TEXT PRIMARY KEY
    , selector_hash             TEXT      NOT NULL
    , origin_location_id        BIGINT    NOT NULL REFERENCES locations(id)
    , origin_label              TEXT
    , input_origin              TEXT      NOT NULL
    , cargo_t                   DOUBLE PRECISION NOT NULL
    , truck_key                 TEXT      NOT NULL
    , ors_profile               TEXT      NOT NULL
    , vessel_class              TEXT
    , include_hoteling          BOOLEAN   NOT NULL DEFAULT TRUE
    , hoteling_hours_per_call   DOUBLE PRECISION
    , port_calls                INTEGER
    , include_port_ops          BOOLEAN   NOT NULL DEFAULT TRUE
    , port_moves_per_call       DOUBLE PRECISION
    , cargo_teu                 DOUBLE PRECISION
    , t_per_teu_default         DOUBLE PRECISION
    , allocation_mode           TEXT
    , allocation_load_factor    DOUBLE PRECISION
    , full_call_mode            BOOLEAN   NOT NULL DEFAULT FALSE
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

CREATE INDEX IF NOT EXISTS idx_bulk_runs_selector_status
    ON bulk_runs (selector_hash, status, updated_timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_bulk_runs_destination_origin
    ON bulk_runs (destination_set_id, status, origin_location_id);

CREATE INDEX IF NOT EXISTS idx_bulk_runs_origin_cargo
    ON bulk_runs (origin_location_id, destination_set_id, cargo_t);

CREATE TABLE IF NOT EXISTS bulk_run_items (
      id                               BIGSERIAL PRIMARY KEY
    , run_id                           TEXT      NOT NULL REFERENCES bulk_runs(run_id) ON DELETE CASCADE
    , scenario_key                     TEXT      NOT NULL
    , input_destiny                    TEXT      NOT NULL
    , destination_location_id          BIGINT    REFERENCES locations(id)
    , port_origin_location_id          BIGINT    REFERENCES locations(id)
    , port_destiny_location_id         BIGINT    REFERENCES locations(id)
    , road_route_id                    BIGINT    REFERENCES route_cache_entries(id)
    , first_mile_route_id              BIGINT    REFERENCES route_cache_entries(id)
    , last_mile_route_id               BIGINT    REFERENCES route_cache_entries(id)
    , status                           TEXT      NOT NULL
    , error_message                    TEXT
    , road_cost_r                      DOUBLE PRECISION
    , multimodal_cost_r                DOUBLE PRECISION
    , cost_delta_r                     DOUBLE PRECISION
    , cost_savings_pct                 DOUBLE PRECISION
    , road_emissions_kg                DOUBLE PRECISION
    , multimodal_emissions_kg          DOUBLE PRECISION
    , emissions_delta_kg               DOUBLE PRECISION
    , emissions_savings_pct            DOUBLE PRECISION
    , road_distance_km                 DOUBLE PRECISION
    , sea_km                           DOUBLE PRECISION
    , is_approximation                 BOOLEAN   NOT NULL DEFAULT FALSE
    , route_source                     TEXT
    , approximation_reference_route_id BIGINT    REFERENCES route_cache_entries(id)
    , approximation_delta_straight_line_km DOUBLE PRECISION
    , approximation_notes              TEXT
    , insertion_timestamp              TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
    , updated_timestamp                TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
    , CONSTRAINT uq_bulk_run_items_run_scenario UNIQUE (run_id, scenario_key)
);

CREATE INDEX IF NOT EXISTS idx_bulk_run_items_run_status
    ON bulk_run_items (run_id, status);

CREATE INDEX IF NOT EXISTS idx_bulk_run_items_run_input_destiny
    ON bulk_run_items (run_id, input_destiny);

CREATE INDEX IF NOT EXISTS idx_bulk_run_items_destination_location
    ON bulk_run_items (destination_location_id);

CREATE OR REPLACE VIEW bulk_run_items_enriched AS
SELECT
      i.id
    , i.run_id
    , i.scenario_key
    , r.selector_hash
    , r.destination_set_id
    , r.origin_location_id
    , COALESCE(NULLIF(TRIM(r.origin_label), ''), NULLIF(TRIM(origin_loc.label), ''), r.origin_location_id::text) AS origin_name
    , r.input_origin
    , i.input_destiny
    , i.destination_location_id
    , COALESCE(NULLIF(TRIM(dest.label), ''), i.input_destiny) AS destiny_name
    , dest.lat6 AS destiny_lat
    , dest.lon6 AS destiny_lon
    , dest.state AS destiny_uf
    , port_origin.label AS port_origin_name
    , port_dest.label AS port_destiny_name
    , r.cargo_t
    , r.truck_key
    , r.ors_profile
    , r.vessel_class
    , r.include_hoteling
    , r.hoteling_hours_per_call
    , r.port_calls
    , r.include_port_ops
    , r.port_moves_per_call
    , r.cargo_teu
    , r.t_per_teu_default
    , r.allocation_mode
    , r.allocation_load_factor
    , r.full_call_mode
    , r.port_ops_scenario
    , i.status
    , i.error_message
    , i.road_cost_r
    , i.multimodal_cost_r
    , i.cost_delta_r
    , i.cost_savings_pct
    , i.road_emissions_kg
    , i.multimodal_emissions_kg
    , i.emissions_delta_kg
    , i.emissions_savings_pct
    , i.road_distance_km
    , i.sea_km
    , i.is_approximation
    , i.route_source
    , approx_dest.label AS approximation_reference_destiny
    , approx_route.distance_km AS approximation_reference_distance_km
    , i.approximation_delta_straight_line_km
    , i.approximation_notes
    , i.insertion_timestamp
    , i.updated_timestamp
FROM bulk_run_items AS i
INNER JOIN bulk_runs AS r
        ON r.run_id = i.run_id
LEFT JOIN locations AS origin_loc
       ON origin_loc.id = r.origin_location_id
LEFT JOIN locations AS dest
       ON dest.id = i.destination_location_id
LEFT JOIN locations AS port_origin
       ON port_origin.id = i.port_origin_location_id
LEFT JOIN locations AS port_dest
       ON port_dest.id = i.port_destiny_location_id
LEFT JOIN route_cache_entries AS approx_route
       ON approx_route.id = i.approximation_reference_route_id
LEFT JOIN locations AS approx_dest
       ON approx_dest.id = approx_route.destiny_location_id;

CREATE TABLE IF NOT EXISTS routes (
      id                  BIGSERIAL PRIMARY KEY
    , origin_key          TEXT      NOT NULL
    , origin_name         TEXT      NOT NULL
    , origin_lat          DOUBLE PRECISION
    , origin_lon          DOUBLE PRECISION
    , destiny_key         TEXT      NOT NULL
    , destiny_name        TEXT      NOT NULL
    , destiny_lat         DOUBLE PRECISION
    , destiny_lon         DOUBLE PRECISION
    , profile_requested   TEXT      NOT NULL DEFAULT 'driving-hgv'
    , profile_used        TEXT
    , lookup_mode         TEXT      NOT NULL DEFAULT 'label'
    , source              TEXT      NOT NULL DEFAULT 'ors'
    , distance_km         DOUBLE PRECISION
    , is_hgv              INTEGER
    , insertion_timestamp TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
    , updated_timestamp   TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_routes_requested_profile
    ON routes (origin_key, destiny_key, profile_requested);

CREATE INDEX IF NOT EXISTS idx_routes_coords_requested_profile
    ON routes (profile_requested, origin_lat, origin_lon, destiny_lat, destiny_lon);

CREATE TABLE IF NOT EXISTS bulk_evaluation_results (
      scenario_key              TEXT PRIMARY KEY
    , origin_name               TEXT      NOT NULL
    , destiny_name              TEXT      NOT NULL
    , input_origin              TEXT      NOT NULL
    , input_destiny             TEXT      NOT NULL
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
    , status                    TEXT      NOT NULL
    , error_message             TEXT
    , geometry_status           TEXT
    , road_direct_source        TEXT
    , first_mile_source         TEXT
    , last_mile_source          TEXT
    , road_direct_profile_used  TEXT
    , first_mile_profile_used   TEXT
    , last_mile_profile_used    TEXT
    , road_distance_km          DOUBLE PRECISION
    , road_fuel_liters          DOUBLE PRECISION
    , road_fuel_kg              DOUBLE PRECISION
    , road_fuel_cost_r          DOUBLE PRECISION
    , road_co2e_kg              DOUBLE PRECISION
    , mm_road_fuel_liters       DOUBLE PRECISION
    , mm_road_fuel_kg           DOUBLE PRECISION
    , mm_road_fuel_cost_r       DOUBLE PRECISION
    , mm_road_co2e_kg           DOUBLE PRECISION
    , sea_km                    DOUBLE PRECISION
    , sea_fuel_kg               DOUBLE PRECISION
    , sea_fuel_cost_r           DOUBLE PRECISION
    , sea_co2e_kg               DOUBLE PRECISION
    , total_fuel_kg             DOUBLE PRECISION
    , total_fuel_cost_r         DOUBLE PRECISION
    , total_co2e_kg             DOUBLE PRECISION
    , delta_cost_r              DOUBLE PRECISION
    , delta_co2e_kg             DOUBLE PRECISION
    , savings_pct               DOUBLE PRECISION
    , diesel_price_r_per_l      DOUBLE PRECISION
    , diesel_price_source       TEXT
    , bunker_price_r_per_t      DOUBLE PRECISION
    , insertion_timestamp       TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
    , updated_timestamp         TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_bulk_evaluation_results_origin_destiny
    ON bulk_evaluation_results (origin_name, destiny_name);

CREATE INDEX IF NOT EXISTS idx_bulk_evaluation_results_status
    ON bulk_evaluation_results (status);

CREATE TABLE IF NOT EXISTS analysis_results (
      origin_name         TEXT      NOT NULL
    , destiny_name        TEXT      NOT NULL
    , cargo_t             DOUBLE PRECISION NOT NULL
    , road_distance_km    DOUBLE PRECISION
    , road_fuel_liters    DOUBLE PRECISION
    , road_fuel_kg        DOUBLE PRECISION
    , road_fuel_cost_r    DOUBLE PRECISION
    , road_co2e_kg        DOUBLE PRECISION
    , mm_road_fuel_liters DOUBLE PRECISION
    , mm_road_fuel_kg     DOUBLE PRECISION
    , mm_road_fuel_cost_r DOUBLE PRECISION
    , mm_road_co2e_kg     DOUBLE PRECISION
    , sea_km              DOUBLE PRECISION
    , sea_fuel_kg         DOUBLE PRECISION
    , sea_fuel_cost_r     DOUBLE PRECISION
    , sea_co2e_kg         DOUBLE PRECISION
    , total_fuel_cost_r   DOUBLE PRECISION
    , total_co2e_kg       DOUBLE PRECISION
    , total_fuel_kg       DOUBLE PRECISION
    , delta_cost_r        DOUBLE PRECISION
    , delta_co2e_kg       DOUBLE PRECISION
    , insertion_timestamp TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_analysis_results_dest
    ON analysis_results (destiny_name);

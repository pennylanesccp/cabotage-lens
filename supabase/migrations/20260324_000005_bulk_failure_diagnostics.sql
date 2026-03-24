ALTER TABLE IF EXISTS bulk_run_items
    ADD COLUMN IF NOT EXISTS failed_step TEXT,
    ADD COLUMN IF NOT EXISTS failed_leg TEXT,
    ADD COLUMN IF NOT EXISTS failure_reason TEXT,
    ADD COLUMN IF NOT EXISTS failure_detail TEXT,
    ADD COLUMN IF NOT EXISTS retryable BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS failure_provider TEXT,
    ADD COLUMN IF NOT EXISTS failure_provider_operation TEXT;

CREATE INDEX IF NOT EXISTS idx_bulk_run_items_run_failure_diag
    ON bulk_run_items (run_id, failed_step, failed_leg, failure_reason);

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
    , i.failed_step
    , i.failed_leg
    , i.failure_reason
    , i.failure_detail
    , COALESCE(i.retryable, FALSE) AS retryable
    , i.failure_provider
    , i.failure_provider_operation
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

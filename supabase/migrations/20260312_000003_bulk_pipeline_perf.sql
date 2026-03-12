CREATE EXTENSION IF NOT EXISTS unaccent;

CREATE TABLE IF NOT EXISTS place_points (
      place_key            TEXT PRIMARY KEY
    , label                TEXT      NOT NULL
    , lat                  DOUBLE PRECISION NOT NULL
    , lon                  DOUBLE PRECISION NOT NULL
    , uf                   TEXT
    , provider             TEXT
    , source               TEXT      NOT NULL DEFAULT 'geocode'
    , insertion_timestamp  TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
    , updated_timestamp    TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_place_points_updated_timestamp
    ON place_points (updated_timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_place_points_label
    ON place_points (label);

INSERT INTO place_points (
      place_key
    , label
    , lat
    , lon
    , provider
    , source
)
SELECT DISTINCT ON (place_key)
      place_key
    , label
    , lat
    , lon
    , provider
    , source
FROM (
    SELECT
          origin_key AS place_key
        , origin_name AS label
        , origin_lat AS lat
        , origin_lon AS lon
        , source AS provider
        , 'route_cache' AS source
        , updated_timestamp
        , insertion_timestamp
    FROM routes
    WHERE origin_key IS NOT NULL
      AND origin_lat IS NOT NULL
      AND origin_lon IS NOT NULL
    UNION ALL
    SELECT
          destiny_key AS place_key
        , destiny_name AS label
        , destiny_lat AS lat
        , destiny_lon AS lon
        , source AS provider
        , 'route_cache' AS source
        , updated_timestamp
        , insertion_timestamp
    FROM routes
    WHERE destiny_key IS NOT NULL
      AND destiny_lat IS NOT NULL
      AND destiny_lon IS NOT NULL
) AS route_points
ORDER BY place_key, updated_timestamp DESC NULLS LAST, insertion_timestamp DESC NULLS LAST, label ASC
ON CONFLICT(place_key) DO UPDATE SET
      label = EXCLUDED.label
    , lat = EXCLUDED.lat
    , lon = EXCLUDED.lon
    , provider = EXCLUDED.provider
    , source = EXCLUDED.source
    , updated_timestamp = CURRENT_TIMESTAMP;

ALTER TABLE routes
    ADD COLUMN IF NOT EXISTS origin_coord_key TEXT,
    ADD COLUMN IF NOT EXISTS destiny_coord_key TEXT;

UPDATE routes
   SET origin_coord_key = TO_CHAR(ROUND(origin_lat::numeric, 5), 'FM999990.00000')
                          || ','
                          || TO_CHAR(ROUND(origin_lon::numeric, 5), 'FM999990.00000'),
       destiny_coord_key = TO_CHAR(ROUND(destiny_lat::numeric, 5), 'FM999990.00000')
                           || ','
                           || TO_CHAR(ROUND(destiny_lon::numeric, 5), 'FM999990.00000')
 WHERE origin_lat IS NOT NULL
   AND origin_lon IS NOT NULL
   AND destiny_lat IS NOT NULL
   AND destiny_lon IS NOT NULL
   AND (
        COALESCE(origin_coord_key, '') = ''
        OR COALESCE(destiny_coord_key, '') = ''
   );

CREATE INDEX IF NOT EXISTS idx_routes_coord_keys_requested_profile
    ON routes (profile_requested, origin_coord_key, destiny_coord_key);

ALTER TABLE bulk_evaluation_results
    ADD COLUMN IF NOT EXISTS input_destiny_key TEXT;

UPDATE bulk_evaluation_results
   SET input_destiny_key = LOWER(unaccent(TRIM(COALESCE(input_destiny, ''))))
 WHERE TRIM(COALESCE(input_destiny, '')) <> ''
   AND COALESCE(input_destiny_key, '') = '';

CREATE INDEX IF NOT EXISTS idx_bulk_evaluation_results_selector_pending
    ON bulk_evaluation_results (
          destination_set_id
        , origin_key
        , cargo_t
        , truck_key
        , ors_profile
        , input_destiny_key
    );

CREATE INDEX IF NOT EXISTS idx_bulk_evaluation_results_selector_updated
    ON bulk_evaluation_results (
          destination_set_id
        , origin_key
        , cargo_t
        , truck_key
        , ors_profile
        , updated_timestamp DESC
    );

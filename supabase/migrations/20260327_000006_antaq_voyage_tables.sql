CREATE TABLE IF NOT EXISTS antaq_voyages (
      voyage_id                  TEXT PRIMARY KEY
    , imo                        TEXT      NOT NULL
    , started_at                 TIMESTAMPTZ
    , ended_at                   TIMESTAMPTZ
    , duration_hours             DOUBLE PRECISION
    , closed_loop                BOOLEAN   NOT NULL DEFAULT FALSE
    , closed_by                  TEXT
    , origin_port_code           TEXT
    , origin_port_name           TEXT
    , destination_port_code      TEXT
    , destination_port_name      TEXT
    , stop_count                 INTEGER   NOT NULL DEFAULT 0
    , intermediate_stop_count    INTEGER   NOT NULL DEFAULT 0
    , call_count_total           INTEGER   NOT NULL DEFAULT 0
    , loaded_teu_total           DOUBLE PRECISION
    , unloaded_teu_total         DOUBLE PRECISION
    , moved_teu_total            DOUBLE PRECISION
    , net_teu_total              DOUBLE PRECISION
    , loaded_weight_t_total      DOUBLE PRECISION
    , unloaded_weight_t_total    DOUBLE PRECISION
    , moved_weight_t_total       DOUBLE PRECISION
    , net_weight_t_total         DOUBLE PRECISION
    , source_generated_at        TIMESTAMPTZ
    , time_enriched_at           TIMESTAMPTZ
    , source_years               JSONB
    , source_files               JSONB
    , filters                    JSONB
    , segmentation               JSONB
    , stats                      JSONB
    , source_file                TEXT      NOT NULL
    , parser_version             TEXT      NOT NULL
    , ingestion_timestamp        TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
    , updated_timestamp          TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_antaq_voyages_imo_started_at
    ON antaq_voyages (imo, started_at DESC);

CREATE INDEX IF NOT EXISTS idx_antaq_voyages_origin_destination
    ON antaq_voyages (origin_port_code, destination_port_code);

CREATE INDEX IF NOT EXISTS idx_antaq_voyages_ingestion_timestamp
    ON antaq_voyages (ingestion_timestamp DESC);

CREATE TABLE IF NOT EXISTS antaq_voyage_stops (
      id                         BIGSERIAL PRIMARY KEY
    , voyage_id                  TEXT      NOT NULL REFERENCES antaq_voyages(voyage_id) ON DELETE CASCADE
    , sequence                   INTEGER   NOT NULL
    , stop_type                  TEXT      NOT NULL
    , port_key                   TEXT
    , port_code                  TEXT
    , port_name                  TEXT
    , atracacao_port_name        TEXT
    , municipality               TEXT
    , state                      TEXT
    , first_atracacao_at         TIMESTAMPTZ
    , last_atracacao_at          TIMESTAMPTZ
    , call_count                 INTEGER   NOT NULL DEFAULT 0
    , loaded_teu                 DOUBLE PRECISION
    , unloaded_teu               DOUBLE PRECISION
    , moved_teu                  DOUBLE PRECISION
    , net_teu                    DOUBLE PRECISION
    , loaded_weight_t            DOUBLE PRECISION
    , unloaded_weight_t          DOUBLE PRECISION
    , moved_weight_t             DOUBLE PRECISION
    , net_weight_t               DOUBLE PRECISION
    , observed_span_hours        DOUBLE PRECISION
    , wait_for_berth_hours       DOUBLE PRECISION
    , wait_for_operation_start_hours DOUBLE PRECISION
    , operation_hours            DOUBLE PRECISION
    , wait_for_departure_hours   DOUBLE PRECISION
    , berth_time_hours           DOUBLE PRECISION
    , port_stay_hours            DOUBLE PRECISION
    , source_row_count           INTEGER   NOT NULL DEFAULT 0
    , missing_call_count         INTEGER   NOT NULL DEFAULT 0
    , source_file                TEXT      NOT NULL
    , parser_version             TEXT      NOT NULL
    , ingestion_timestamp        TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
    , updated_timestamp          TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
    , CONSTRAINT uq_antaq_voyage_stops_voyage_sequence UNIQUE (voyage_id, sequence)
    , CONSTRAINT ck_antaq_voyage_stops_stop_type CHECK (stop_type IN ('origin', 'intermediate', 'destination'))
);

CREATE INDEX IF NOT EXISTS idx_antaq_voyage_stops_port_code
    ON antaq_voyage_stops (port_code);

CREATE INDEX IF NOT EXISTS idx_antaq_voyage_stops_voyage_id
    ON antaq_voyage_stops (voyage_id);

CREATE INDEX IF NOT EXISTS idx_antaq_voyage_stops_first_atracacao_at
    ON antaq_voyage_stops (first_atracacao_at);

CREATE TABLE IF NOT EXISTS antaq_voyage_stop_calls (
      id                         BIGSERIAL PRIMARY KEY
    , voyage_id                  TEXT      NOT NULL REFERENCES antaq_voyages(voyage_id) ON DELETE CASCADE
    , stop_sequence              INTEGER   NOT NULL
    , call_order                 INTEGER   NOT NULL DEFAULT 1
    , call_id                    TEXT      NOT NULL
    , source_file                TEXT      NOT NULL
    , parser_version             TEXT      NOT NULL
    , ingestion_timestamp        TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
    , updated_timestamp          TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
    , CONSTRAINT uq_antaq_voyage_stop_calls_call_id UNIQUE (call_id)
    , CONSTRAINT fk_antaq_voyage_stop_calls_stop FOREIGN KEY (voyage_id, stop_sequence)
        REFERENCES antaq_voyage_stops (voyage_id, sequence) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_antaq_voyage_stop_calls_voyage_stop
    ON antaq_voyage_stop_calls (voyage_id, stop_sequence, call_order);

CREATE TABLE IF NOT EXISTS antaq_voyages_raw (
      voyage_id                  TEXT PRIMARY KEY REFERENCES antaq_voyages(voyage_id) ON DELETE CASCADE
    , imo                        TEXT      NOT NULL
    , source_generated_at        TIMESTAMPTZ
    , time_enriched_at           TIMESTAMPTZ
    , source_file                TEXT      NOT NULL
    , parser_version             TEXT      NOT NULL
    , ingestion_timestamp        TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
    , updated_timestamp          TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
    , raw_payload                JSONB     NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_antaq_voyages_raw_imo
    ON antaq_voyages_raw (imo);

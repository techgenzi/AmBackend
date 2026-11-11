CREATE TABLE IF NOT EXISTS process_incentive_slabs (
    id BIGSERIAL PRIMARY KEY,
    activity_stage_map_id BIGINT,
    from_qty NUMERIC,
    to_qty NUMERIC,
    incentive_amount NUMERIC,
    compcode BIGINT,
    created_on TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    modified_on TIMESTAMP,
    modified_by VARCHAR(150),
    deleted_at TIMESTAMP,
    deleted BOOLEAN DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_process_incentive_slabs_map_id ON process_incentive_slabs(activity_stage_map_id);

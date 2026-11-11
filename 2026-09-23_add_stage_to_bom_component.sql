ALTER TABLE bom_component ADD COLUMN stage_id BIGINT;
ALTER TABLE bom_component ADD CONSTRAINT fk_bom_comp_stage FOREIGN KEY (stage_id) REFERENCES stage (stage_id);
CREATE INDEX IF NOT EXISTS idx_bom_component_stage_id ON bom_component(stage_id);

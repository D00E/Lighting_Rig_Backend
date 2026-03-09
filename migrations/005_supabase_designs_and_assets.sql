CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS designs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    callsign TEXT UNIQUE NOT NULL,
    design_type TEXT NOT NULL,
    gif_name TEXT NOT NULL,
    creator TEXT,
    description TEXT,
    num_frames INT NOT NULL DEFAULT 0,
    num_packets INT NOT NULL DEFAULT 0,
    download_count INT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE designs ADD COLUMN IF NOT EXISTS callsign TEXT;
ALTER TABLE designs ADD COLUMN IF NOT EXISTS design_type TEXT;
ALTER TABLE designs ADD COLUMN IF NOT EXISTS gif_name TEXT;
ALTER TABLE designs ADD COLUMN IF NOT EXISTS creator TEXT;
ALTER TABLE designs ADD COLUMN IF NOT EXISTS description TEXT;
ALTER TABLE designs ADD COLUMN IF NOT EXISTS num_frames INT NOT NULL DEFAULT 0;
ALTER TABLE designs ADD COLUMN IF NOT EXISTS num_packets INT NOT NULL DEFAULT 0;
ALTER TABLE designs ADD COLUMN IF NOT EXISTS download_count INT NOT NULL DEFAULT 0;
ALTER TABLE designs ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW();
ALTER TABLE designs ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'callsign_length'
          AND conrelid = 'designs'::regclass
    ) THEN
        ALTER TABLE designs
        ADD CONSTRAINT callsign_length CHECK (char_length(callsign) = 6);
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'num_frames_nonnegative'
          AND conrelid = 'designs'::regclass
    ) THEN
        ALTER TABLE designs
        ADD CONSTRAINT num_frames_nonnegative CHECK (num_frames >= 0);
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'num_packets_nonnegative'
          AND conrelid = 'designs'::regclass
    ) THEN
        ALTER TABLE designs
        ADD CONSTRAINT num_packets_nonnegative CHECK (num_packets >= 0);
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'download_count_nonnegative'
          AND conrelid = 'designs'::regclass
    ) THEN
        ALTER TABLE designs
        ADD CONSTRAINT download_count_nonnegative CHECK (download_count >= 0);
    END IF;
END $$;

CREATE UNIQUE INDEX IF NOT EXISTS uq_designs_callsign ON designs (callsign);

CREATE TABLE IF NOT EXISTS design_assets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    design_id UUID NOT NULL REFERENCES designs(id) ON DELETE CASCADE,
    asset_type TEXT NOT NULL,
    storage_bucket TEXT NOT NULL,
    storage_path TEXT NOT NULL,
    content_type TEXT,
    size_bytes BIGINT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE design_assets ADD COLUMN IF NOT EXISTS design_id UUID;
ALTER TABLE design_assets ADD COLUMN IF NOT EXISTS asset_type TEXT;
ALTER TABLE design_assets ADD COLUMN IF NOT EXISTS storage_bucket TEXT;
ALTER TABLE design_assets ADD COLUMN IF NOT EXISTS storage_path TEXT;
ALTER TABLE design_assets ADD COLUMN IF NOT EXISTS content_type TEXT;
ALTER TABLE design_assets ADD COLUMN IF NOT EXISTS size_bytes BIGINT;
ALTER TABLE design_assets ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'design_assets_design_id_fkey'
          AND conrelid = 'design_assets'::regclass
    ) THEN
        ALTER TABLE design_assets
        ADD CONSTRAINT design_assets_design_id_fkey
        FOREIGN KEY (design_id) REFERENCES designs(id) ON DELETE CASCADE;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_design_assets_design_id ON design_assets (design_id);
CREATE UNIQUE INDEX IF NOT EXISTS uq_design_assets_design_id_asset_type ON design_assets (design_id, asset_type);

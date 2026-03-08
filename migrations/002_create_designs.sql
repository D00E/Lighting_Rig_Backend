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
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT callsign_length CHECK (char_length(callsign) = 6),
    CONSTRAINT num_frames_nonnegative CHECK (num_frames >= 0),
    CONSTRAINT num_packets_nonnegative CHECK (num_packets >= 0)
);
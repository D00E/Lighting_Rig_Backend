CREATE TABLE IF NOT EXISTS user_favourites (
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    design_id UUID NOT NULL REFERENCES designs(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (user_id, design_id)
);
CREATE TABLE IF NOT EXISTS provider_blocked_dates (
    id SERIAL PRIMARY KEY,
    provider_id INTEGER NOT NULL REFERENCES providers(id),
    blocked_date DATE NOT NULL,
    reason VARCHAR(255),
    CONSTRAINT uq_provider_blocked_date UNIQUE (provider_id, blocked_date)
);
-- Strava Analytics - PostgreSQL Schema
-- Run this script in Supabase SQL Editor to initialize the database

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Drop existing tables if they exist (for clean reinstall)
DROP TABLE IF EXISTS activity_streams CASCADE;
DROP TABLE IF EXISTS training_loads CASCADE;
DROP TABLE IF EXISTS training_zones CASCADE;
DROP TABLE IF EXISTS activities CASCADE;
DROP TABLE IF EXISTS oauth_tokens CASCADE;
DROP TABLE IF EXISTS sync_metadata CASCADE;
DROP TABLE IF EXISTS athletes CASCADE;

-- Athletes table
CREATE TABLE athletes (
    id BIGINT PRIMARY KEY,
    username VARCHAR(255),
    firstname VARCHAR(255),
    lastname VARCHAR(255),
    profile_medium VARCHAR(500),
    profile VARCHAR(500),
    city VARCHAR(255),
    state VARCHAR(255),
    country VARCHAR(255),
    sex VARCHAR(1),
    weight FLOAT,
    ftp INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- OAuth tokens table
CREATE TABLE oauth_tokens (
    id SERIAL PRIMARY KEY,
    athlete_id BIGINT NOT NULL REFERENCES athletes(id) ON DELETE CASCADE,
    access_token VARCHAR(255) NOT NULL,
    refresh_token VARCHAR(255) NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    token_type VARCHAR(20) DEFAULT 'Bearer',
    scope VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Activities table
CREATE TABLE activities (
    id BIGINT PRIMARY KEY,
    athlete_id BIGINT NOT NULL REFERENCES athletes(id) ON DELETE CASCADE,
    name VARCHAR(500),
    type VARCHAR(50),
    sport_type VARCHAR(50),
    start_date TIMESTAMP NOT NULL,
    start_date_local TIMESTAMP,
    timezone VARCHAR(100),
    distance FLOAT,
    moving_time INTEGER,
    elapsed_time INTEGER,
    total_elevation_gain FLOAT,
    average_speed FLOAT,
    max_speed FLOAT,
    average_heartrate FLOAT,
    max_heartrate FLOAT,
    average_cadence FLOAT,
    average_watts FLOAT,
    max_watts FLOAT,
    kilojoules FLOAT,
    calories FLOAT,
    suffer_score FLOAT,
    workout_type INTEGER,
    description TEXT,
    gear_id VARCHAR(100),
    map_polyline TEXT,
    map_summary_polyline TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Activity streams table (detailed time-series data)
CREATE TABLE activity_streams (
    id SERIAL PRIMARY KEY,
    activity_id BIGINT NOT NULL REFERENCES activities(id) ON DELETE CASCADE,
    stream_type VARCHAR(50) NOT NULL,
    data JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Training loads table (CTL/ATL/TSB)
CREATE TABLE training_loads (
    id SERIAL PRIMARY KEY,
    athlete_id BIGINT NOT NULL REFERENCES athletes(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    daily_tss FLOAT,
    ctl FLOAT,
    atl FLOAT,
    tsb FLOAT,
    fitness_level VARCHAR(50),
    form_status VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(athlete_id, date)
);

-- Training zones table
CREATE TABLE training_zones (
    id SERIAL PRIMARY KEY,
    athlete_id BIGINT NOT NULL REFERENCES athletes(id) ON DELETE CASCADE,
    zone_type VARCHAR(20) NOT NULL,
    zone_number INTEGER NOT NULL,
    min_value FLOAT,
    max_value FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(athlete_id, zone_type, zone_number)
);

-- Sync metadata table
CREATE TABLE sync_metadata (
    id SERIAL PRIMARY KEY,
    athlete_id BIGINT NOT NULL REFERENCES athletes(id) ON DELETE CASCADE,
    last_full_sync TIMESTAMP,
    last_incremental_sync TIMESTAMP,
    last_stream_sync TIMESTAMP,
    total_activities_synced INTEGER DEFAULT 0,
    sync_status VARCHAR(50),
    sync_error TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(athlete_id)
);

-- Indexes for performance
CREATE INDEX idx_activities_athlete_date ON activities(athlete_id, start_date DESC);
CREATE INDEX idx_activities_type ON activities(type);
CREATE INDEX idx_activities_sport_type ON activities(sport_type);
CREATE INDEX idx_activity_streams_activity ON activity_streams(activity_id, stream_type);
CREATE INDEX idx_training_loads_athlete_date ON training_loads(athlete_id, date DESC);
CREATE INDEX idx_oauth_tokens_athlete ON oauth_tokens(athlete_id);
CREATE INDEX idx_oauth_tokens_expires ON oauth_tokens(expires_at);

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Triggers for updated_at
CREATE TRIGGER update_athletes_updated_at BEFORE UPDATE ON athletes
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_oauth_tokens_updated_at BEFORE UPDATE ON oauth_tokens
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_activities_updated_at BEFORE UPDATE ON activities
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_training_loads_updated_at BEFORE UPDATE ON training_loads
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_training_zones_updated_at BEFORE UPDATE ON training_zones
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_sync_metadata_updated_at BEFORE UPDATE ON sync_metadata
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Grant permissions (for Supabase service role)
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO postgres;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO postgres;

-- Success message
DO $$
BEGIN
    RAISE NOTICE 'Database schema initialized successfully!';
    RAISE NOTICE 'Tables created: athletes, oauth_tokens, activities, activity_streams, training_loads, training_zones, sync_metadata';
    RAISE NOTICE 'Indexes and triggers configured';
END $$;

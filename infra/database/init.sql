-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Enable TimescaleDB extension (already included in timescaledb/postgresql image)
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Create pgvector extension for LLM embeddings
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

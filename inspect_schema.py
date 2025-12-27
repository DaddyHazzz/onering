#!/usr/bin/env python3
"""Quick script to inspect database schema."""

from sqlalchemy import inspect, create_engine
import os

url = os.getenv('DATABASE_URL', 'postgresql://user:pass@localhost:5432/onering')
engine = create_engine(url)
inspector = inspect(engine)

tables = ['analytics_events', 'idempotency_keys', 'drafts', 'draft_segments', 'draft_collaborators', 'ring_passes']

for table in tables:
    print(f'\n=== {table} ===')
    print('Indexes:')
    for idx in inspector.get_indexes(table):
        print(f"  {idx['name']}: {idx['column_names']}")
    
    print('Unique Constraints:')
    for c in inspector.get_unique_constraints(table):
        print(f"  {c['name']}: {c['column_names']}")

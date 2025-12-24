#!/usr/bin/env python3
"""Check if persistence is enabled"""

import os
from backend.features.collaboration.service import _use_persistence, _get_persistence

print(f"DATABASE_URL: {os.getenv('DATABASE_URL')}")
print(f"_use_persistence(): {_use_persistence()}")
print(f"_get_persistence(): {_get_persistence()}")

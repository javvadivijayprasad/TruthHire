import os
os.environ["DATABASE_URL"] = "sqlite://"   # shared in-memory (StaticPool) for the test session
from app.db import init_db
from app.auth import seed_keys
init_db()
seed_keys()

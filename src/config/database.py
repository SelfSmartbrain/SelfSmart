"""
SmartSelf AI - Database & Cache Configuration
Centralizes connection logic for PostgreSQL and Redis.
"""

import logging
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import redis
from src.config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# PostgreSQL
DATABASE_URL = getattr(settings, "database_url", "postgresql://user:password@localhost/smartself")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Redis Cache
REDIS_URL = getattr(settings, "redis_url", "redis://localhost:6379/0")
redis_client = redis.from_url(REDIS_URL, decode_responses=True)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_cache():
    return redis_client

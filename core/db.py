import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from pydantic_settings import BaseSettings
from typing import Generator

class DatabaseSettings(BaseSettings):
    """Database configuration from environment"""
    database_url: str

    class Config:
        env_file = ".env"

# Initialize settings
db_settings = DatabaseSettings()

# Create SQLAlchemy engine
engine = create_engine(
    db_settings.database_url,
    pool_pre_ping=True,
    pool_recycle=300
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()

def get_db() -> Generator[Session, None, None]:
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

"""Common dependencies for FastAPI dependency injection"""
import uuid
from datetime import datetime, timezone
from typing import Generator

from fastapi import Depends
from sqlalchemy.orm import Session

from core.db import SessionLocal
from generation.clients.model_client import StubModelClient, IdeaModelClient


def get_db_session() -> Generator[Session, None, None]:
    """
    Database session dependency.

    Yields:
        Session: SQLAlchemy database session
    """
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def get_trace_id() -> str:
    """
    Generate unique trace ID for request tracking.

    Returns:
        str: Unique trace ID
    """
    return f"api_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"


def get_model_client() -> IdeaModelClient:
    """
    Model client dependency.

    v1: Returns StubModelClient for testing
    v2: Will support real Claude/OpenAI clients based on configuration

    Returns:
        IdeaModelClient: Model client instance
    """
    return StubModelClient()
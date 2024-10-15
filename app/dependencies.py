from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
)
from app.config.db import engine
from typing import AsyncGenerator
from app.config.settings import settings
import redis.asyncio as aioredis

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as db:
        yield db 
        
async def get_redis():
    redis_client = aioredis.from_url(f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}")
    return redis_client
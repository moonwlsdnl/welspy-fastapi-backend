from sqlalchemy.ext.asyncio import (
    create_async_engine,
)
from sqlalchemy.orm import declarative_base
from .settings import settings
from urllib.parse import quote
from sqlalchemy import Column, Integer, String, Float, Enum, DateTime
from app.enums.enum import CategoryEnum

Base = declarative_base()

DATABASE_URL = f'mysql+aiomysql://{settings.DB_USER}:{quote(settings.DB_PASSWORD)}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}'

# 비동기 엔진 생성
engine = create_async_engine(DATABASE_URL, echo=True)

class UserSimilarity(Base):
    __tablename__ = "user_similarity"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_a = Column(String(255), nullable=False, index=True) 
    user_b = Column(String(255), nullable=False, index=True) 
    similarity_score = Column(Float, nullable=False)

class TempUserAction(Base):
    __tablename__ = "temp_user_action"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    challenge_id = Column(Integer, nullable=False, index=True)
    user_email = Column(String(255), nullable=False, index=True)
    category = Column(Enum(CategoryEnum), nullable=False)
    start_time = Column(DateTime, nullable=False)

async def create_all():
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    except Exception as e:
        print(f"Error creating tables: {e}")


from fastapi import FastAPI, Depends
from app.config.settings import settings
from app.config.db import create_all
from app.dependencies import get_db, get_redis
from sqlalchemy.ext.asyncio import AsyncSession
from app.apis import routers
from app.apis.recommendations.service import RecommendationsService
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# Lifespan 이벤트 핸들러 정의
async def lifespan_event(app: FastAPI):
    # 애플리케이션 시작 시 데이터베이스 테이블 생성
    await create_all()
    
    async for db in get_db():
        redis_client = await get_redis()
        service = await create_recommendations_service(db, redis_client)
        await service.fetch_and_save_data()
        
    yield 
    
# FastAPI 애플리케이션 생성
app = FastAPI(
    title=settings.TITLE,
    description=settings.DESCRIPTION,
    lifespan=lifespan_event,
)

async def create_recommendations_service(db: AsyncSession = Depends(get_db), redis_client = Depends(get_redis)):
    return RecommendationsService(db, redis_client)

# APScheduler 설정
scheduler = AsyncIOScheduler()

# 주기적으로 데이터를 가져오는 작업 추가
async def fetch_and_save_data():
    async for db in get_db():
        service = await create_recommendations_service(db)
        await service.fetch_and_save_data()

scheduler.add_job(fetch_and_save_data, 'interval', seconds=3600) # 1시간 마다 한번씩 실행
scheduler.start()

origins = [
    "*",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True, # 쿠키 포함 여부
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
for router in routers:
    app.include_router(router)
    
# 헬스 체크
@app.get("/")
def root():
    return {"message": "FastAPI is running!"}



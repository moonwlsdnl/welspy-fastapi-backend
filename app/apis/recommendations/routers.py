from fastapi import APIRouter, Depends
from app.dependencies import get_db, get_redis
from sqlalchemy.ext.asyncio import AsyncSession
from app.apis.recommendations.schemas import RequestDto, ResponseDto
from app.apis.recommendations.service import RecommendationsService

router = APIRouter()

@router.post("/recommendations", response_model=list)
async def recommendations(request: RequestDto, db: AsyncSession = Depends(get_db), redis_client = Depends(get_redis)):
    user_email = request.user_email
    page = request.page
    size = request.size

    service = RecommendationsService(db, redis_client)

    # Redis에서 캐시된 데이터 확인
    cached_data = await service.get_cached_challenges(user_email)
    print(f"cached_data: {cached_data}")
    if cached_data:
        return cached_data  # Redis에서 데이터 반환

    # 유사한 사용자
    similar_users = await service.get_similar_users(user_email)

    # temp_user_action 테이블에서 챌린지 구하기
    challenges = await service.get_user_challenges(similar_users)

    # 모든 챌린지를 count하고 정렬
    sorted_challenges = await service.count_and_sort_challenges(challenges)

    # 페이지네이션 처리
    paginated_challenges = await service.paginate_challenges(sorted_challenges, page, size)

    # 결과를 Redis에 저장 (TTL 6시간)
    await service.cache_challenges(user_email, paginated_challenges)

    return {"roomIds": paginated_challenges}
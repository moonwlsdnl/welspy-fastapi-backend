from fastapi import APIRouter, Depends, Query
from app.dependencies import get_db, get_redis
from sqlalchemy.ext.asyncio import AsyncSession
from app.apis.recommendations.schemas import ResponseDto
from app.apis.recommendations.service import RecommendationsService

router = APIRouter()

@router.get("/recommendations", response_model=ResponseDto)
async def recommendations(
    user_email: str = Query(..., description="User email"),
    page: int = Query(1, description="Page number"),
    size: int = Query(10, description="Page size"),
    db: AsyncSession = Depends(get_db),
    redis_client = Depends(get_redis)
):
    service = RecommendationsService(db, redis_client)

    # Redis에서 캐시된 데이터 확인
    cached_data = await service.get_cached_challenges(user_email)
    print(f"cached_data: {cached_data}")

    if cached_data:
        paginated_challenges = await service.paginate_challenges(cached_data, page=page, size=size)
        return {"roomIds": paginated_challenges}

    # 유사한 사용자
    similar_users = await service.get_similar_users(user_email)
    print(similar_users)

    # temp_user_action 테이블에서 챌린지 구하기
    challenges = await service.get_user_challenges(similar_users)
    print(challenges)

    # 모든 챌린지를 count하고 정렬
    sorted_challenges = await service.count_and_sort_challenges(challenges)

    # 전체 챌린지를 Redis에 저장 (TTL 6시간)
    await service.cache_challenges(user_email, sorted_challenges)

    # 페이지네이션 처리
    paginated_challenges = await service.paginate_challenges(sorted_challenges, page, size)
    print(paginated_challenges)

    return {"roomIds": paginated_challenges}

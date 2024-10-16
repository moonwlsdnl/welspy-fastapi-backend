from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.future import select
from sqlalchemy import func, text
from sklearn.metrics.pairwise import cosine_similarity
import pandas as pd
import requests
from fastapi import HTTPException
from app.config.db import TempUserAction, UserSimilarity
from sqlalchemy import case
from datetime import timedelta
import httpx
import pickle

class RecommendationsService:
    def __init__(self, db: AsyncSession, redis_client):
        self.db = db
        self.redis_client = redis_client

        
    # 6시간 마다 temp_user_action 테이블 업데이트
    async def fetch_and_save_data(self):
        try:
            # 외부 API에서 데이터 가져오기
            async with httpx.AsyncClient() as client:
                response = await client.get("http://13.125.208.1:8080/data")

            # 응답 실패 시 예외 처리
            if response.status_code != 200:
                raise HTTPException(status_code=500, detail="외부 API에서 데이터를 가져오는 데 실패했습니다.")

            data = response.json()['data']
            
            # 기존 데이터 삭제
            await self.db.execute(text("DELETE FROM temp_user_action"))
            await self.db.commit()

            # 새 데이터 저장
            for item in data:
                new_action = TempUserAction(
                    user_email=item['userEmail'],
                    challenge_id=item['challengeId'],
                    category=item['category'],
                    start_time=item['startTime']
                )
                self.db.add(new_action)

            await self.db.commit()
            
            # 유사도 계산 실행
            await self.calculate_similarity()

        except SQLAlchemyError as e:
            await self.db.rollback()  # DB 트랜잭션 롤백
            raise HTTPException(status_code=500, detail="데이터베이스 오류가 발생했습니다.")

        except HTTPException as e:
            raise HTTPException(status_code=500, detail=f"오류가 발생했습니다: {str(e)}")

    
    async def calculate_similarity(self):
        query = select(
            TempUserAction.user_email,
            func.sum(case((TempUserAction.category == 'TRAVEL', 1), else_=0)).label('TRAVEL'),
            func.sum(case((TempUserAction.category == 'DIGITAL', 1), else_=0)).label('DIGITAL'),
            func.sum(case((TempUserAction.category == 'FASHION', 1), else_=0)).label('FASHION'),
            func.sum(case((TempUserAction.category == 'TOYS', 1), else_=0)).label('TOYS'),
            func.sum(case((TempUserAction.category == 'INTERIOR', 1), else_=0)).label('INTERIOR'),
            func.sum(case((TempUserAction.category == 'ETC', 1), else_=0)).label('ETC')
        ).group_by(TempUserAction.user_email)

        result = await self.db.execute(query)
        user_category_matrix = pd.DataFrame(result.fetchall(), columns=result.keys())
        print(user_category_matrix)
        
        user_category_matrix.set_index('user_email', inplace=True)

        cosine_sim = cosine_similarity(user_category_matrix)
        similarity_df = pd.DataFrame(cosine_sim, index=user_category_matrix.index, columns=user_category_matrix.index)
        print(similarity_df)

        await self.db.execute(text("DELETE FROM user_similarity"))
        
        new_similarities = []
        for user1 in similarity_df.index:
            for user2 in similarity_df.columns:
                if user1 == user2:
                    continue 
                similarity_value = similarity_df.loc[user1, user2]
                if similarity_value > 0: 
                    new_similarity = UserSimilarity(user_a=user1, user_b=user2, similarity_score=similarity_value)
                    new_similarities.append(new_similarity)

        self.db.add_all(new_similarities)
        await self.db.commit()

        print(f"A total of {len(new_similarities)} similarity records have been created.")

    # 유사한 사용자 5명 구하기
    async def get_similar_users(self, user_email: str):
        query = select(UserSimilarity.user_b).where(UserSimilarity.user_a == user_email).order_by(UserSimilarity.similarity_score.desc()).limit(5)
        result = await self.db.execute(query)
        return [row[0] for row in result.fetchall()]
    
    # user_email에 해당하는 모든 챌린지 조회
    async def get_user_challenges(self, similar_users: str):
        query = (
            select(TempUserAction.challenge_id)
            .where(TempUserAction.user_email.in_(similar_users))
        )

        result = await self.db.execute(query)
        return [row[0] for row in result.fetchall()]
    
    # 외부 서버에서 전체 챌린지 ID 가져오기
    async def fetch_all_challenges(self):
        async with httpx.AsyncClient() as client:
            response = await client.get("http://13.125.208.1:8080/data/id")
            if response.status_code != 200:
                raise HTTPException(status_code=500, detail="Failed to fetch challenges from external API")
            return [item['roomId'] for item in response.json()['data']]


    # 챌린지를 count하고 빈도수가 높은 순서로 정렬
    async def count_and_sort_challenges(self, challenges: list):
        challenge_counts = pd.Series(challenges).value_counts().reset_index()
        challenge_counts.columns = ['challenge_id', 'count']
        sorted_challenges = challenge_counts.sort_values(by='count', ascending=False)

        sorted_challenges_list = sorted_challenges['challenge_id'].tolist()
        print(f"Sorted challenges: {sorted_challenges_list}")

        external_challenges = await self.fetch_all_challenges()

        unique_external_challenges = [challenge for challenge in external_challenges if challenge not in sorted_challenges_list]

        combined_challenges = sorted_challenges_list + unique_external_challenges
        print(f"Combined challenges: {combined_challenges}")
        
        return combined_challenges


    # 요청받은 page와 size에 따라 챌린지를 페이지네이션 처리
    async def paginate_challenges(self, sorted_challenges: list, page: int, size: int):
        page_index = page - 1
        
        total_challenges = len(sorted_challenges)
        max_page = (total_challenges // size) + (1 if total_challenges % size > 0 else 0)

        # 요청한 페이지가 범위를 초과하면 빈 데이터 반환
        if page_index >= max_page or page_index < 0:
            return []

        start_index = page_index * size
        end_index = start_index + size
        
        return sorted_challenges[start_index:end_index]

    # 챌린지를 Redis에 직렬화하여 저장
    async def cache_challenges(self, user_email: str, challenges: list):
        serialized_challenges = pickle.dumps(challenges)
        await self.redis_client.setex(user_email, timedelta(hours=6), serialized_challenges)

    # Redis에서 캐시된 챌린지 데이터 조회
    async def get_cached_challenges(self, user_email: str):
        cached_data = await self.redis_client.get(user_email)
        if cached_data:
            return pickle.loads(cached_data)
        return None
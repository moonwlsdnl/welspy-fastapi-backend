from pydantic import BaseModel

class ResponseDto(BaseModel):
    roomIds: list[int]
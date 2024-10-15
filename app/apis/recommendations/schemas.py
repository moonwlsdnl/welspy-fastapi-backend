from pydantic import BaseModel

class RequestDto(BaseModel):
    page: int
    size: int
    user_email: str

class ResponseDto(BaseModel):
    roomIds: list[int]
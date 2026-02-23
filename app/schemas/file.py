from pydantic import BaseModel


class PresignRequest(BaseModel):
    original_name: str
    content_type: str


class PresignResponse(BaseModel):
    url: str
    method: str
    bucket: str
    object_key: str
    expires_in: int

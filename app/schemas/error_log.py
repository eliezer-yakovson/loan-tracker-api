from pydantic import BaseModel


class ErrorLogCreate(BaseModel):
    context: str = ""
    message: str
    details: str = ""
    created_at: str  # ISO timestamp from client


class ErrorLogRead(BaseModel):
    id: str
    user_id: str
    created_at: str
    context: str
    message: str
    details: str

    model_config = {"from_attributes": True}

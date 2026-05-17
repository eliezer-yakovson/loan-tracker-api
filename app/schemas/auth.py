from pydantic import BaseModel, EmailStr, field_validator


class RegisterRequest(BaseModel):
    email: EmailStr
    name: str

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("שם לא יכול להיות ריק")
        return v


class RegisterVerifyRequest(BaseModel):
    email: EmailStr
    code: str
    name: str

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("שם לא יכול להיות ריק")
        return v


class SendOTPRequest(BaseModel):
    email: EmailStr
    purpose: str = "login"  # "login" | "register" | "reset"


class VerifyOTPRequest(BaseModel):
    email: EmailStr
    code: str
    purpose: str = "login"


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    email: str
    name: str
    is_admin: bool = False


class UserOut(BaseModel):
    id: str
    email: str
    name: str
    created_at: str
    is_active: bool
    is_admin: bool

    model_config = {"from_attributes": True}

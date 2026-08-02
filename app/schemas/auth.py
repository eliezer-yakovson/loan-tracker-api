from pydantic import BaseModel, EmailStr, Field, field_validator

_MIN_PASSWORD_LEN = 8
_MAX_PASSWORD_LEN = 128


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
    # Optional: set a password during registration so the user can also log in
    # with email + password (not only via an emailed OTP code).
    password: str | None = Field(default=None, min_length=_MIN_PASSWORD_LEN, max_length=_MAX_PASSWORD_LEN)

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("שם לא יכול להיות ריק")
        return v


class PasswordLoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=_MAX_PASSWORD_LEN)


class SetPasswordRequest(BaseModel):
    password: str = Field(min_length=_MIN_PASSWORD_LEN, max_length=_MAX_PASSWORD_LEN)


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
    has_password: bool = False

    model_config = {"from_attributes": True}

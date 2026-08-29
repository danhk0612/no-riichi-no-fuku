from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    login_id: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=8, max_length=128)
    player_name: str = Field(min_length=1, max_length=80)


class LoginRequest(BaseModel):
    login_id: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    must_change_password: bool

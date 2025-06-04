# MVP/auth_new/schemas_new.py

from pydantic import BaseModel, EmailStr

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    user_id: int | None = None

class User(BaseModel):
    id: int
    email: EmailStr
    username: str
    is_active: bool = True

class UserCreate(BaseModel):
    email: EmailStr
    password: str
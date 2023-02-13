from __future__ import annotations

from pydantic import BaseModel, EmailStr


class UserIn(BaseModel):
    password: str
    email: EmailStr
    is_active: bool


class UserOut(BaseModel):
    id: int
    email: EmailStr
    is_active: bool

    class Config:
        orm_mode = True


class UserList(BaseModel):
    __root__: list[UserOut]


class UserUpdate(BaseModel):
    password: str | None = None
    email: EmailStr | None = None
    is_active: bool | None = None

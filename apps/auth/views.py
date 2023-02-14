from fastapi import status, HTTPException, Depends, APIRouter
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from apps.users.models import User
from database.base import get_db
from apps.auth.utils import (
    create_access_token,
    create_refresh_token,
    verify_password,
    user_from_refresh_token
)
from apps.auth.serializers import TokenSchema, AccessTokenGETSchema

router = APIRouter(
    prefix="/auth",
    tags=["auth"],
    responses={404: {"description": "Not found"}},
)


@router.post('/login/', summary="Create access and refresh tokens for user", response_model=TokenSchema)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form_data.username).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect email or password"
        )

    hashed_pass = user.password
    if not verify_password(form_data.password, hashed_pass):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect email or password"
        )

    return {
        "access_token": create_access_token(user.email),
        "refresh_token": create_refresh_token(user.email),
    }


@router.post('/token/', summary='Get new access token given refresh token', response_model=TokenSchema)
async def get_access_token(data: AccessTokenGETSchema = Depends()):
    email = user_from_refresh_token(data.refresh_token)

    return {
        "access_token": create_access_token(email),
        "refresh_token": data.refresh_token,
    }

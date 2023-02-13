from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database.base import get_db
from .models import User
from .serializers import UserIn, UserOut, UserList, UserUpdate

router = APIRouter(
    prefix="/users",
    tags=["users"],
    responses={404: {"description": "Not found"}},
)


@router.get("/", response_model=UserList)
async def get_all_user(db: Session = Depends(get_db)):
    return db.query(User).all()


@router.get("/{user_id}/", response_model=UserOut)
async def get_user(user_id: int, db: Session = Depends(get_db)):
    return db.query(User) \
        .filter(User.id == user_id) \
        .first()


@router.post("/", response_model=UserOut)
def create_user(user: UserIn, db: Session = Depends(get_db)):
    new_user = User(**(user.dict()))
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user


@router.patch("/{user_id}/", response_model=UserOut)
async def update_user(user_id: int, user: UserUpdate, db: Session = Depends(get_db)):
    user_query = db.query(User) \
        .filter(User.id == user_id)
    _user = user_query.first()
    if _user:
        user_query.update(user.dict(exclude_unset=True))
        db.commit()
        return user_query.first()


@router.delete("/{user_id}/")
async def get_user(user_id: int, db: Session = Depends(get_db)):
    db.query(User) \
        .filter(User.id == user_id) \
        .delete()

    db.commit()
    return {"status": "success"}

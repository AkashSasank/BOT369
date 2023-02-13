from fastapi import APIRouter, Request
from apps.trading_platform.zerodha.kite import Kite

router = APIRouter(
    prefix="/kite",
    tags=["kite"],
    responses={404: {"description": "Not found"}},
)


@router.get('/token/')
def get_access_token(request_token: str = None):
    kite = Kite('v21wcpfmc0cqzym5', 'w1kyh62lp4zgvlpfnnsfdi90tlyu367w', 'http://localhost:8000/token/')
    access_token = kite.connect(request_token)
    return {
        'access_token': access_token
    }


@router.get('/login/')
def login():
    kite = Kite('v21wcpfmc0cqzym5', 'w1kyh62lp4zgvlpfnnsfdi90tlyu367w', 'http://localhost:8000/token/')
    return {
        'url': kite.get_login_url()
    }

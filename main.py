from fastapi import FastAPI

from fastapi.staticfiles import StaticFiles
from apps.users import views as user_views
from apps.config import views as config_views
from apps.trading_platform.zerodha import views as kite_views
from apps.auth import views as auth_views

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
app.include_router(user_views.router)
app.include_router(config_views.router)
app.include_router(kite_views.router)
app.include_router(auth_views.router)

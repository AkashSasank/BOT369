from fastapi import FastAPI
import uvicorn
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from starlette.middleware import Middleware
from starlette.middleware.authentication import AuthenticationMiddleware
from apps.auth.middleware import JWTAuthMiddleware
from apps.users import views as user_views
from apps.config import views as config_views
from apps.trading_platform.zerodha import views as kite_views
from apps.auth import views as auth_views

app = FastAPI(middleware=[JWTAuthMiddleware])

app.mount("/static", StaticFiles(directory="static"), name="static")
app.include_router(user_views.router)
app.include_router(config_views.router)
app.include_router(kite_views.router)
app.include_router(auth_views.router)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

from starlette.authentication import (
    AuthCredentials, AuthenticationBackend, AuthenticationError, SimpleUser
)
from starlette.middleware import Middleware
from starlette.middleware.authentication import AuthenticationMiddleware
from apps.auth.utils import decode_access_token


class User(SimpleUser):
    def __str__(self):
        return self.username


class JWTAuthBackend(AuthenticationBackend):
    async def authenticate(self, conn):
        if "Authorization" not in conn.headers:
            return

        auth = conn.headers["Authorization"]
        try:
            scheme, credentials = auth.split()
            if scheme.lower() != 'bearer':
                return
            decoded = decode_access_token(credentials)
        except Exception as exc:
            raise AuthenticationError('Invalid token')

        username = decoded['sub']
        return AuthCredentials(["authenticated"]), User(username)


JWTAuthMiddleware = Middleware(AuthenticationMiddleware, backend=JWTAuthBackend())

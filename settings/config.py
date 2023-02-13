import os

from pydantic import BaseSettings


class EnvSettings(BaseSettings):
    SQLALCHEMY_DATABASE_URL: str

    class Config:
        env_file = f"{os.path.dirname(os.path.abspath(__file__))}/.env"


settings = EnvSettings()


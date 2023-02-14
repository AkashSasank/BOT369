from pydantic import BaseModel


class BotCredentialsPostSchema(BaseModel):
    api_key: str
    api_secret: str
    redirect_url: str
    postback_url: str

from enum import Enum


class TradingPlatform(Enum):
    ZERODHA = 'ZERODHA'

    def __str__(self):
        return self.value


class SecretKeys(Enum):
    API_KEY = 'API_KEY'
    API_SECRET = 'API_SECRET'
    REDIRECT_URL = 'REDIRECT_URL'
    ACCESS_TOKEN = 'ACCESS_TOKEN'

    def __str__(self):
        return self.value

from kiteconnect import KiteConnect
from utils.base.broker import Broker


class Kite(Broker):

    def __init__(self, api_key, api_secret, redirect_url):
        self.api_key = api_key
        self.api_secret = api_secret
        self.redirect_url = redirect_url
        self.kite_connect = KiteConnect(api_key=self.api_key)

    def connect(self, request_token):
        data = self.kite_connect.generate_session(request_token, api_secret=self.api_secret)
        access_token = data["access_token"]
        self.kite_connect.set_access_token(access_token)
        return access_token

    def get_login_url(self):
        return self.kite_connect.login_url()

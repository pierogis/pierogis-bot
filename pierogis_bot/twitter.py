import secrets
import time

import requests
from requests_oauthlib import OAuth1
import os
import json


# To set your environment variables in your terminal run the following line:
# export 'BEARER_TOKEN'='<your_bearer_token>'

class Api:
    def __init__(self, bearer_token, oauth_consumer_key, oauth_consumer_secret):
        self.bearer_token = bearer_token
        self.oauth_consumer_key = oauth_consumer_key
        self.oauth_consumer_secret = oauth_consumer_secret

    def get_auth(self, user_oauth_token, user_oauth_secret):
        return OAuth1(self.oauth_consumer_key, self.oauth_consumer_secret,
                      resource_owner_key=user_oauth_token, resource_owner_secret=user_oauth_secret)

    @property
    def headers(self):
        return {'Authorization': "Bearer {}".format(self.bearer_token)}

    def post_for_request_token(self):
        url = "https://api.twitter.com/oauth/request_token"
        params = {
            'oauth_callback': "oob",
            'oauth_consumer_key': self.oauth_consumer_key
        }

        response = requests.post(url=url, params=params, headers=self.headers)

        return response

    def post_for_access_token(self, pin, request_token, request_token_secret):
        url = "https://api.twitter.com/oauth/access_token"
        params = {
            'oauth_token': request_token,
            'oauth_verifier': pin
        }

        auth = self.get_auth(request_token, request_token_secret)
        response = requests.post(url=url, params=params, auth=auth)

        return response

    def post_status_update(self, status, user_oauth_token, user_oauth_secret):
        url = "https://api.twitter.com/1.1/statuses/update.json"
        params = {
            'status': status
        }

        auth = self.get_auth(user_oauth_token, user_oauth_secret)
        response = requests.post(url=url, params=params, auth=auth)

        return response

    def user_mentions(user_id):
        params = {"tweet.fields": "created_at"}
        return "https://api.twitter.com/2/users/{}/mentions".format(user_id)

import json
import os

from pierogis_bot import Api


def schedule_tweet(event, context):
    status = "pierogi"
    oauth_access_token = os.getenv('OAUTH_ACCESS_TOKEN')
    oauth_access_token_secret = os.getenv('OAUTH_ACCESS_TOKEN_SECRET')

    bearer_token = os.getenv('BEARER_TOKEN')
    oauth_consumer_key = os.getenv('OAUTH_CONSUMER_KEY')
    oauth_consumer_secret = os.getenv('OAUTH_CONSUMER_SECRET')

    api = Api(bearer_token, oauth_consumer_key, oauth_consumer_secret)
    status_update_response = api.post_status_update(status, oauth_access_token, oauth_access_token_secret)

    return status_update_response

    # Use this code if you don't use the http event with the LAMBDA-PROXY
    # integration
    """
    return {
        "message": "Go Serverless v1.0! Your function executed successfully!",
        "event": event
    }
    """

import os
from dotenv import load_dotenv

from pierogis_bot import Bot

if __name__ == '__main__':
    print('Select function to test')

    load_dotenv(".env")

    oauth_consumer_key = os.getenv('OAUTH_CONSUMER_KEY')
    oauth_consumer_secret = os.getenv('OAUTH_CONSUMER_SECRET')
    bearer_token = os.getenv('BEARER_TOKEN')

    oauth_access_token = os.getenv('OAUTH_ACCESS_TOKEN')
    oauth_access_token_secret = os.getenv('OAUTH_ACCESS_TOKEN_SECRET')

    batch_request_queue_url = os.getenv('BATCH_REQUEST_QUEUE_URL')
    tweets_media_queue_url = os.getenv('TWEETS_MEDIA_QUEUE_URL')
    user_id = os.getenv('USER_ID')

    bot = Bot(
        bearer_token, oauth_consumer_key, oauth_consumer_secret,
        oauth_access_token=oauth_access_token, oauth_access_token_secret=oauth_access_token_secret,
        batch_request_queue_url=batch_request_queue_url,
        tweets_media_queue_url=tweets_media_queue_url,
        user_id=user_id
    )

    bot.poll_mentions(None, None)

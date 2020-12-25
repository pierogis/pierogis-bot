import os
from dotenv import load_dotenv

from pierogis_bot import Bot

print('Select function to test')

load_dotenv(".env")

oauth_consumer_key = os.getenv('OAUTH_CONSUMER_KEY')
oauth_consumer_secret = os.getenv('OAUTH_CONSUMER_SECRET')
bearer_token = os.getenv('BEARER_TOKEN')

oauth_access_token = os.getenv('OAUTH_ACCESS_TOKEN')
oauth_access_token_secret = os.getenv('OAUTH_ACCESS_TOKEN_SECRET')

recipes_batch_requests_topic_url = os.getenv('recipes_batch_requests_topic_url')
batch_requests_bucket = os.getenv('BATCH_REQUESTS_BUCKET')
user_id = os.getenv('USER_ID')

bot = Bot(
    bearer_token, oauth_consumer_key, oauth_consumer_secret,
    oauth_access_token=oauth_access_token, oauth_access_token_secret=oauth_access_token_secret,
    recipes_batch_requests_topic_url=recipes_batch_requests_topic_url, batch_requests_bucket=batch_requests_bucket,
    user_id=user_id
)

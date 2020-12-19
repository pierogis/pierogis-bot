import os

from dotenv import load_dotenv

from pierogis_bot import Api

load_dotenv("./.env")

oauth_consumer_key = os.getenv('OAUTH_CONSUMER_KEY')
oauth_consumer_secret = os.getenv('OAUTH_CONSUMERSECRET')
bearer_token = os.getenv('BEARER_TOKEN')

oauth_access_token = os.getenv('OAUTH_ACCESS_TOKEN')
oauth_access_token_secret = os.getenv('OAUTH_ACCESS_TOKEN_SECRET')

user_id = os.getenv('OAUTH_ACCESS_TOKEN_SECRET')

def schedule_tweet(event, context):
    status = "pierogi"

    api = Api(
        bearer_token, oauth_consumer_key, oauth_consumer_secret
    )

    media = None

    media_id = api.post_media_upload(media, oauth_access_token, oauth_access_token_secret)
    status_update_response = api.post_status_update(status, media_id=media_id)

    return status_update_response




def respond_mention(event, context):
    api = Api(
        bearer_token, oauth_consumer_key, oauth_consumer_secret
    )

    # check for new mentions
    # for new mention
    # if image
    # post their image to api|pierogis
    # post response image to twitter media upload
    # post status linking to that media_id and replying to the og tweet id

    media = None
    status = None

    media_id = api.post_media_upload(media, oauth_access_token, oauth_access_token_secret)
    status_update_response = api.post_status_update(status, media_id, oauth_access_token, oauth_access_token_secret)

    return status_update_response


def respond_dm(event, context):
    pass


if __name__ == '__main__':
    print('Select function to test')

    schedule_tweet(None, None)

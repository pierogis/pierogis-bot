from twitter import Api


class Bot:
    """
    Handler class for serverless
    """

    allowed_media_types = ['image/png']

    def __init__(self, bearer_token, oauth_consumer_key, oauth_consumer_secret, user_id = None, oauth_access_token: str = None,
                 oauth_access_token_secret: str = None):
        self.user_id = user_id
        self.api = Api(bearer_token, oauth_consumer_key, oauth_consumer_secret)

        self.oauth_access_token = oauth_access_token
        self.oauth_access_token_secret = oauth_access_token_secret

    def poll_mentions(self, event, context):
        api = Api()
        json = api.get_users_mentions(self.user_id, tweet_fields=['referenced_tweets'])

        expansions = json['data']

        for mention in json['data']:
            # look for media in tweet
            # look for media above this tweet
            entities = mention.get('entities')
            for entitity in entities:
                urls = entitity['urls']

                for url in urls:
                    url['display_url']

            if attachments & attachments.get('media_type') in self.allowed_media_types:
                batch = {
                    'media_id': media_id
                }
            else:
                tweet.get('in_reply_to_id')
            # LAMBDA.invoke(
            #     FunctionName=TWEET_PROCESSOR_FUNCTION_NAME,
            #     InvocationType='Event',
            #     Payload=json.dumps(batch)
            # )

        # should also poll replies

    def
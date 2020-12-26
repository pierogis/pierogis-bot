import io
import json

import boto3 as boto3
import requests

from .chef import Chef
from .twitter import Twitter


class Bot:
    """
    Handler class for serverless
    """

    allowed_media_types = ['photo']
    sqs = boto3.resource('sqs')
    s3 = boto3.resource('s3')

    def __init__(self, bearer_token, oauth_consumer_key, oauth_consumer_secret,
                 meal_requests_bucket_name, user_id=None, oauth_access_token: str = None,
                 oauth_access_token_secret: str = None, meal_chef_arn=None
                 ):
        """

        :param bearer_token:
        :param oauth_consumer_key:
        :param oauth_consumer_secret:
        :param user_id:
        :param oauth_access_token:
        :param oauth_access_token_secret:
        """
        self.user_id = user_id
        self.twitter = Twitter(bearer_token, oauth_consumer_key, oauth_consumer_secret)
        self.chef = Chef()

        self.oauth_access_token = oauth_access_token
        self.oauth_access_token_secret = oauth_access_token_secret

        self.meal_chef_arn = meal_chef_arn
        self.meal_requests_bucket = self.s3.Bucket(meal_requests_bucket_name)

    def poll_mentions(self):
        """
        Get mentions for the user and distill them into dish batch requests

        :param event:
        :param context:
        :return:
        """
        mentions_response = self.twitter.get_users_mentions(
            self.user_id, tweet_fields=['author_id', 'referenced_tweets'],
            expansions=['attachments.media_keys', 'author_id'], media_fields=['type', 'url'],
            user_fields=['username']
        )

        expanded_users = self.__get_expanded_users(mentions_response)

        # get expanded media from json response
        expanded_media = self.__get_expanded_media(mentions_response)
        mentions = mentions_response['data']
        meal_inputs = []
        # loop through the tweets in the response
        for mention in mentions:
            # try process remaining media that got exploded if it is in this tweet
            dishes = []

            # if there was included media, try to create dishes for media in the current tweet
            if len(expanded_media) > 0:
                dishes = self.__get_tweet_dishes(mention, expanded_media)

            # if there aren't any dishes from the current tweet and the caller indicated recurse
            if len(dishes) < 1:
                # look up tweets referenced by this tweet
                referenced_ids = [referenced_tweet['id'] for referenced_tweet in mention['referenced_tweets']]
                # get
                referenced_tweets_response = self.__get_referenced_tweets(referenced_ids)
                expanded_media = self.__get_expanded_media(referenced_tweets_response)

                referenced_tweets = referenced_tweets_response['data']
                if len(expanded_media) > 0:
                    for tweet in referenced_tweets:
                        dishes.extend(self.__get_tweet_dishes(tweet, expanded_media))

            if len(dishes) > 0:
                meal_id = mention['id']
                username = expanded_users[mention['author_id']]['username']

                for dish in dishes:
                    dish['mealId'] = meal_id

                meal_input = {
                    'dishes': dishes,
                    'mealId': meal_id,
                    'username': username
                }
                meal_inputs.append(meal_input)

        return meal_inputs

    def __get_tweet_dishes(self, tweet, expanded_media):
        media_keys = tweet.get('attachments', {}).get('media_keys')
        dishes = []
        for media_key in media_keys:
            # loop through this mentions attachments
            medium_metadata = expanded_media.pop(media_key, None)
            if medium_metadata is not None:
                dish = {
                    'ingredients': {
                        'pierogi': {
                            'args': {},
                            'kwargs': {
                                'path': 0
                            }
                        }
                    },
                    'recipe': [
                        'pierogi'
                    ],
                    'urls': [
                        medium_metadata['url']
                    ]
                }

                dishes.append(dish)

        return dishes

    def __get_expanded_users(self, tweets_response):
        """
        getting the expanded media in the response if any

        :param media_dict:
        :return:
        """

        included_users_dicts = tweets_response.get('includes', {}).get('users')
        # if there was media in the response, turn it into a dict keyed by media key with values for url and type
        expanded_media = {}
        if included_users_dicts is not None:
            expanded_media = {}
            for user in included_users_dicts:
                expanded_media[user['id']] = {'username': user['username']}

        return expanded_media

    def __get_expanded_media(self, tweets_response):
        """
        getting the expanded media in the response if any

        :param media_dict:
        :return:
        """

        included_media_dicts = tweets_response.get('includes', {}).get('media')
        # if there was media in the response, turn it into a dict keyed by media key with values for url and type
        expanded_media = {}
        if included_media_dicts is not None:
            expanded_media = {}
            for item in included_media_dicts:
                if item['type'] in self.allowed_media_types:
                    expanded_media[item['media_key']] = {'type': item['type'], 'url': item['url']}

        return expanded_media

    def __get_referenced_tweets(self, referenced_ids):
        # get the media from a set of tweets
        tweets_response = self.twitter.get_tweets(
            referenced_ids,
            expansions=['attachments.media_keys'], media_fields=['type',
                                                                 'url']
        )

        return tweets_response

    def download_ingredients(self, meal_id, urls):
        # receive media urls to download and put in s3
        i = 0
        keys = []
        for url in urls:
            response = requests.get(url, stream=True)
            file = io.BytesIO(response.content)

            extension = url.split('.')[-1]

            object_name = '/'.join(['input_media', str(meal_id), str(i) + '.' + extension])
            self.meal_requests_bucket.upload_fileobj(file, object_name)

            keys.append(object_name)

            i += 1

        return keys

    def cook_dish(self, meal_id, ingredients_dict, recipe, input_keys):
        # receive ingredients, recipe, and s3 keys to cook a dish and store in s3
        images = []
        for key in input_keys:
            image = io.BytesIO()
            self.meal_requests_bucket.download_fileobj(key, image)
            images.append(image)

        output_key = '/'.join(['output_media', meal_id, '0' + '.png'])

        with io.BytesIO() as file:
            self.chef.cook_json_pierogi(file, ingredients_dict, recipe, images)

            file.seek(0)
            self.meal_requests_bucket.upload_fileobj(file, output_key)

        return output_key

    def reply_tweet(self, keys, username, meal_id):
        media_ids = []
        for key in keys:
            file = io.BytesIO()
            self.meal_requests_bucket.download_fileobj(key, file)

            media_id = self.twitter.post_media_upload(file, self.oauth_access_token, self.oauth_access_token_secret)
            media_ids.append(media_id)

        status = "@{}".format(username)

        self.twitter.post_status_update(status, self.oauth_access_token, self.oauth_access_token_secret,
                                        media_ids=media_ids, reply_id=meal_id)

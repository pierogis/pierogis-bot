import io
import json
import uuid

import boto3 as boto3
import requests
from pierogis import Chef

from .twitter import Twitter


class Bot:
    """
    Handler class for serverless
    """

    allowed_media_types = ['photo']
    sqs = boto3.resource('sqs')
    s3 = boto3.resource('s3')

    def __init__(self, bearer_token, oauth_consumer_key, oauth_consumer_secret,
                 orders_bucket_name, user_id=None,
                 oauth_access_token: str = None, oauth_access_token_secret: str = None
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

        self.orders_bucket = self.s3.Bucket(orders_bucket_name)

    def get_orders(self, since_id):
        """
        Get mentions for the user and distill them into dish batch requests

        :param event:
        :param context:
        :return:
        """
        mentions_response = self.twitter.get_users_mentions(
            self.user_id, since_id=since_id,
            tweet_fields=['author_id', 'referenced_tweets'],
            expansions=['attachments.media_keys'],
            media_fields=['type', 'url']
        )

        # get expanded media from json response
        expanded_media = self.__get_expanded_media(mentions_response)
        mentions = mentions_response.get('data')
        orders = []

        if mentions is not None:
            # loop through the tweets in the response
            for mention in mentions:
                # try process remaining media that got exploded if it is in this tweet
                dishes = []

                if mention['author_id'] == self.user_id:
                    continue

                mention_text = mention.get('text')
                media_keys = mention.get('attachments', {}).get('media_keys', [])

                # if there was included media, try to create dishes for media in the current tweet
                if len(expanded_media) > 0:
                    dishes = self.__get_tweet_dishes(mention_text, media_keys, expanded_media)

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
                            if tweet['author_id'] == self.user_id:
                                continue

                            media_keys = tweet.get('attachments', {}).get('media_keys', [])
                            dishes.extend(self.__get_tweet_dishes(mention_text, media_keys, expanded_media))

                if len(dishes) > 0:
                    order_id = str(uuid.uuid4())
                    tweet_id = mention['id']

                    for dish in dishes:
                        dish['orderId'] = order_id

                    order = {
                        'orderId': order_id,
                        'tweet_id': tweet_id,
                        'author_id': mention['author_id'],
                        'dishes': dishes
                    }

                    orders.append(order)

        return orders

    def __get_tweet_dishes(self, tweet_text, media_keys, expanded_media):
        dishes = []

        if len(media_keys) > 0:
            recipe_text = ' '.join(tweet_text.split()[1:-1])

            if recipe_text == '':
                recipe_text = 'sort'

            for media_key in media_keys:
                # loop through this mentions attachments
                medium_metadata = expanded_media.pop(media_key, None)
                if medium_metadata is not None:
                    # get json from the ingredients list
                    ingredients = {}
                    seasoning_links = {}
                    recipes = []
                    file_links = {}
                    self.chef.create_pierogi_desc(ingredients, seasoning_links, recipes, file_links,
                                                  medium_metadata['url'])

                    ingredients, season_links, recipes, file_links = self.chef.read_recipe(ingredients, seasoning_links,
                                                                                           recipes,
                                                                                           file_links, recipe_text)
                    dish = {
                        'ingredients': ingredients,
                        'seasoningLinks': seasoning_links,
                        'recipes': recipes,
                        'fileLinks': file_links
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

    def download_ingredients(self, order_id, file_links):
        # receive media urls to download and put in s3
        i = 0
        for file_uuid, url in file_links.items():
            response = requests.get(url, stream=True)
            file = io.BytesIO(response.content)

            extension = url.split('.')[-1]

            object_name = '/'.join(['input_media', str(order_id), str(i) + '.' + extension])
            self.orders_bucket.upload_fileobj(file, object_name)

            file_links[file_uuid] = object_name

            i += 1

        return file_links

    def cook_dish(self, order_id, ingredient_descs, seasoning_links, recipe_orders, file_links):
        # receive ingredients, recipe, and s3 keys to cook a dish and store in s3
        for ingredient_uuid, s3_key in file_links.items():
            path = '/tmp/' + order_id + '-' + s3_key.split('/')[-1]
            self.orders_bucket.download_file(s3_key, path)
            file_links[ingredient_uuid] = path

        output_filename = order_id + '.png'
        output_key = '/'.join(['output_media', output_filename])

        output_path = '/'.join(['/tmp', output_filename])
        cooked_dish = self.chef.cook_dish_desc(ingredient_descs, seasoning_links, recipe_orders, file_links)
        cooked_dish.save(output_path)
        self.orders_bucket.upload_file(output_path, output_key)

        return output_key

    def reply_tweet(self, tweet_id, author_id, keys):
        media_ids = []
        for key in keys:
            file_object = self.orders_bucket.Object(key)
            path = '/tmp/' + key.split('/')[-1]
            file_object.download_file(path)

            media_id = self.twitter.post_media_upload(path, self.oauth_access_token, self.oauth_access_token_secret)
            media_ids.append(media_id)

        user_lookup_response = self.twitter.get_username(author_id)
        status = '@' + user_lookup_response['data']['username']

        self.twitter.post_status_update(status, self.oauth_access_token, self.oauth_access_token_secret,
                                        media_ids=media_ids, reply_id=tweet_id)

import uuid

from pyrogis import Chef

from .twitter import Twitter


class Bot:
    """
    Handler class for serverless
    """

    allowed_media_types = ['photo']

    def __init__(self, bearer_token, oauth_consumer_key, oauth_consumer_secret,
                 user_id=None,
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

    def __get_tweet_order(self, tweet, expanded_media):
        dishes = []

        if tweet['author_id'] == self.user_id:
            return

        mention_text = tweet.get('text')
        media_keys = tweet.get('attachments', {}).get('media_keys', [])

        # if there was included media, try to create dishes for media in the current tweet
        if len(expanded_media) > 0:
            dishes = self.__get_tweet_dishes(mention_text, media_keys, expanded_media)

        # if there aren't any dishes from the current tweet and the caller indicated recurse
        if len(dishes) < 1:
            # look up tweets referenced by this tweet
            referenced_ids = [referenced_tweet['id'] for referenced_tweet in tweet['referenced_tweets']]
            # get
            referenced_tweets_response = self.__get_referenced_tweets(referenced_ids)
            expanded_media = self.__get_expanded_media(referenced_tweets_response)

            referenced_tweets = referenced_tweets_response['data']
            if len(expanded_media) > 0:
                for referenced_tweet in referenced_tweets:
                    if referenced_tweet['author_id'] == self.user_id:
                        continue

                    media_keys = referenced_tweet.get('attachments', {}).get('media_keys', [])
                    dishes.extend(self.__get_tweet_dishes(mention_text, media_keys, expanded_media))

        if len(dishes) > 0:
            order_id = str(uuid.uuid4())
            tweet_id = tweet['id']

            for dish in dishes:
                dish['orderId'] = order_id

            order = {
                'orderId': order_id,
                'tweet_id': tweet_id,
                'author_id': tweet['author_id'],
                'dishes': dishes
            }

            return order

    def __get_tweet_dishes(self, tweet_text, media_keys, expanded_media):
        dishes = []

        if len(media_keys) > 0:
            tweet_phrases = tweet_text.split()

            while len(tweet_phrases) > 0 and tweet_phrases[0][0] == '@':
                tweet_phrases.pop(0)

            recipe_text = ' '.join(tweet_phrases)

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
            tweet_fields=['author_id'],
            expansions=['attachments.media_keys'], media_fields=['type',
                                                                 'url']
        )

        return tweets_response

    def get_mention_orders(self, since_id: str):
        """
        Get mentions for the user and distill them into dish batch requests

        :param since_id: the id to check mentions since
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
                order = self.__get_tweet_order(mention, expanded_media)
                if order is not None:
                    orders.append(order)

        return orders

    def cook_dish(self, ingredient_descs, seasoning_links, recipe_orders, file_links):
        """
        receive dish description, cook, and store in tmp

        :param ingredient_descs:
        :param seasoning_links:
        :param recipe_orders:
        :param file_links:
        :return:
        """

        cooked_dish = self.chef.cook_dish_desc(ingredient_descs, seasoning_links, recipe_orders, file_links)

        return cooked_dish

    def reply_tweet(self, tweet_id, author_id, paths):
        media_ids = []
        for path in paths:
            media_id = self.twitter.post_media_upload(path, self.oauth_access_token, self.oauth_access_token_secret)
            media_ids.append(media_id)

        user_lookup_response = self.twitter.get_username(author_id)
        status = '@' + user_lookup_response['data']['username']

        self.twitter.post_status_update(status, self.oauth_access_token, self.oauth_access_token_secret,
                                        media_ids=media_ids, reply_id=tweet_id)

    def get_id_orders(self, ids: list, recipe):
        tweets_response = self.twitter.get_tweets(ids, tweet_fields=['author_id', 'referenced_tweets'],
                                                  expansions=['attachments.media_keys'],
                                                  media_fields=['type', 'url'])

        expanded_media = self.__get_expanded_media(tweets_response)
        tweets = tweets_response.get('data')
        orders = []

        if tweets is not None:
            # loop through the tweets in the response
            for tweet in tweets:
                tweet['text'] = recipe

                order = self.__get_tweet_order(tweet, expanded_media)
                if order is None:
                    continue

                orders.append(order)

        return orders

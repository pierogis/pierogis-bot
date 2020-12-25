import io

import boto3 as boto3
import requests

from .twitter import Twitter


class Bot:
    """
    Handler class for serverless
    """

    allowed_media_types = ['photo']
    sqs = boto3.resource('sqs')
    s3 = boto3.resource('s3')

    def __init__(self, bearer_token, oauth_consumer_key, oauth_consumer_secret, user_id=None,
                 oauth_access_token: str = None, oauth_access_token_secret: str = None,
                 recipes_batch_requests_topic_url=None, batch_requests_bucket=None
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

        self.oauth_access_token = oauth_access_token
        self.oauth_access_token_secret = oauth_access_token_secret

        self.recipes_batch_requests_topic_url = recipes_batch_requests_topic_url
        self.batch_requests_bucket = self.s3.Bucket(batch_requests_bucket)

    def poll_mentions(self, event, context):
        json = self.twitter.get_users_mentions(
            self.user_id, tweet_fields=['author_id', 'referenced_tweets'],
            expansions=['attachments.media_keys'], media_fields=['type',
                                                                 'url']
        )

        # dispatch message to image processing with urls
        # get media from referenced tweets (stragglers)
        # dispatch these urls to the image processing

        expanded_media = self.__get_expanded_media(json)

        dishes = []
        referenced_id_sets = []

        mentions = json['data']
        for mention in mentions:
            # try process remaining media that got exploded if it is in this tweet
            try:
                media_keys = mention['attachments']['media_keys']
                for media_key in media_keys:
                    # loop through this mentions attachments
                    medium_metadata = expanded_media.pop(media_key)

                    dish = {
                        'id': mention['id'],
                        'recipe': [
                            {

                                'ingredient': 'pierogi',
                                'path': medium_metadata['url']
                            }
                        ]
                    }

                dishes.append(dish)

            except:
                # need to look up referenced tweets and handle their media
                referenced_id_sets.append(
                    [referenced_tweet['id'] for referenced_tweet in mention['referenced_tweets']]
                )

        # send this set of recipes to the queue
        self.__dispatch_dishes_requests(dishes)

        media_to_process = self.__get_referenced_media(referenced_id_sets)

        self.__dispatch_batch_requests(media_to_process)

    def __get_expanded_media(self, json):
        """
        getting the expanded media in the response if any

        :param json:
        :return:
        """
        media = {}
        includes = json.get('includes')
        if includes:
            raw_media = includes.get('media')
            # if one of the mentions had media directly in it add it to a dict called media
            if raw_media:
                for item in raw_media:
                    if item['type'] in self.allowed_media_types:
                        media[item['media_key']] = {'type': item['type'], 'url': item['url']}

        return media

    def __dispatch_recipes(self, recipes):
        """

        :param id: the status id to respond to
        :param url: the url to process
        :param type: image
        :return:
        """
        # these are tweets in the response
        entries = []
        for recipe in recipes:
            entry = {
                        'Id': medium['mention_id'],
                        'MessageBody': recipe,
                    },

            entries.append(entry)

        queue = self.sqs.Queue(self.store_batch_requests_queue_url)

        queue.send_messages(
            Entries=entries
        )

    def __get_referenced_media(self, referenced_id_sets):
        # get the media from a set of tweets
        referenced_ids = [referenced_ids for referenced_ids in referenced_id_sets]
        json = self.twitter.get_tweets(
            referenced_ids,
            expansions=['attachments.media_keys'], media_fields=['type',
                                                                 'url']
        )

        media = self.__get_expanded_media(json)

        return media

    def download_recipe(self, event, context):
        # receive media urls to download and put in s3
        records = event['Records']
        for record in records:
            mention_id = record['messageId']
            recipe = record['body']

            bucket_name = self.batch_requests_bucket
            object_name = '/'.join(['recipes', mention_id + '.json'])
            s3_object = self.s3.Object(bucket_name, object_name)
            s3_object.put(Body=recipe)

            i = 0
            for url in urls:
                response = requests.get(url, stream=True)
                file = io.BytesIO(response.content)

                extension = url.split('.')[-1]

                bucket_name = self.batch_requests_bucket
                object_name = '/'.join(['batch_requests', mention_id, str(i) + extension])
                s3_object = self.s3.Object(bucket_name, object_name)
                s3_object.upload_fileobj(file)

                i += 1

    def cook_recipe(self, event, context):
        # receive media urls to download and put in s3
        records = event['Records']
        for record in records:
            object_name = record['s3']['object']['key']
            self.batch_requests_bucket.Object(object_name)
            file = self.s3.get_file(bucket_name, object_name)

            apply_manipulation(file)

            response = requests.get(url, stream=True)
            file = io.BytesIO(response.content)

            bucket_name = self.batch_requests_bucket
            object_name = '/'.join(['recipes_batch_requests', mention_id, str(i)])
            self.s3.upload_fileobj(file, bucket_name, object_name)

    def reply_tweet(self, event, context):
        keys = event['keys']
        reply_id = event['mention_id']
        username = event['username']

        bucket_name = self.batch_requests_bucket
        s3_bucket = self.s3.Bucket(bucket_name)

        media_ids = []
        for key in keys:
            file = io.BytesIO()
            s3_bucket.download_fileobj(key, file)

            media_id = self.twitter.post_media_upload(file, self.oauth_access_token, self.oauth_access_token_secret)
            media_ids.append(media_id)

        status = "@{}".format(username)

        self.twitter.post_status_update(status, self.oauth_access_token, self.oauth_access_token_secret,
                                        media_ids=media_ids, reply_id=reply_id)

import boto3 as boto3
import requests

from .twitter import Api


class Bot:
    """
    Handler class for serverless
    """

    allowed_media_types = ['photo']
    sqs = boto3.client('sqs')
    s3 = boto3.client('s3')

    def __init__(self, bearer_token, oauth_consumer_key, oauth_consumer_secret, user_id=None,
                 oauth_access_token: str = None, oauth_access_token_secret: str = None,
                 store_batch_request_queue_url=None, batch_request_bucket=None
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
        self.api = Api(bearer_token, oauth_consumer_key, oauth_consumer_secret)

        self.oauth_access_token = oauth_access_token
        self.oauth_access_token_secret = oauth_access_token_secret

        self.store_batch_request_queue_url = store_batch_request_queue_url
        self.batch_request_bucket = batch_request_bucket

    def poll_mentions(self, event, context):
        json = self.api.get_users_mentions(
            self.user_id, tweet_fields=['author_id', 'referenced_tweets'],
            expansions=['attachments.media_keys'], media_fields=['type',
                                                                 'url']
        )

        # dispatch message to image processing with urls
        # get media from referenced tweets (stragglers)
        # dispatch these urls to the image processing

        expanded_media = self.__get_expanded_media(json)

        media_to_process = []
        referenced_id_sets = []

        mentions = json['data']
        for mention in mentions:
            # try process remaining media that got exploded if it is in this tweet
            try:
                media_keys = mention['attachments']['media_keys']
                urls = []
                for media_key in media_keys:
                    # loop through this mentions attachments
                    medium_metadata = expanded_media.pop(media_key)
                    urls.append(medium_metadata['url'])

                medium = {
                    'reply_id': mention['id'],
                    'urls': urls
                }

                media_to_process.append(medium)

            except:
                # need to look up referenced tweets and handle their media
                referenced_id_sets.append(
                    [referenced_tweet['id'] for referenced_tweet in mention['referenced_tweets']]
                )

        self.__dispatch_batch_request(media_to_process)

        media_to_process = self.__get_referenced_media(referenced_id_sets)

        self.__dispatch_batch_request(media_to_process)

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

    def __dispatch_batch_request(self, media):
        """

        :param id: the status id to respond to
        :param url: the url to process
        :param type: image
        :return:
        """
        # these are tweets in the response
        entries = []
        for medium in media:
            entry = {
                'Id': medium['mention_id'],
                'MessageBody': ','.join(medium['urls'])
            }

            entries.append(entry)

        self.sqs.send_message_batch(
            QueueUrl=self.store_batch_request_queue_url,
            Entries=entries
        )

    def __get_referenced_media(self, referenced_id_sets):
        # get the media from a set of tweets
        referenced_ids = [referenced_ids for referenced_ids in referenced_id_sets]
        json = self.api.get_tweets(
            referenced_ids,
            expansions=['attachments.media_keys'], media_fields=['type',
                                                                 'url']
        )

        media = self.__get_expanded_media(json)

        return media

    def store_batch_request(self, event, context):
        # receive media urls to download and put in s3
        records = event['Records']
        for record in records:
            mention_id = record['messageId']
            urls_string = record['body']
            urls = urls_string.split(',')

            i = 0
            for url in urls:
                file = requests.get(url)

                bucket_name = self.batch_request_bucket
                object_name = mention_id + '/' + i
                self.s3.upload_fileobj(file, bucket_name, object_name)

                i += 1

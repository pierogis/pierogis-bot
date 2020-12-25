import functools
import secrets
import time

import requests
from requests_oauthlib import OAuth1


class Twitter:
    oauth_request_url = "https://api.twitter.com/oauth/request_token"
    oauth_access_url = "https://api.twitter.com/oauth/access_token"

    users_mentions_url = "https://api.twitter.com/2/users/{}/mentions"
    statuses_update_url = "https://api.twitter.com/1.1/statuses/update.json"
    media_upload_url = "https://upload.twitter.com/1.1/media/upload.json"
    get_tweets_url = "https://api.twitter.com/2/tweets"

    def __init__(self, bearer_token, oauth_consumer_key, oauth_consumer_secret):
        self.bearer_token = bearer_token
        self.oauth_consumer_key = oauth_consumer_key
        self.oauth_consumer_secret = oauth_consumer_secret

    @property
    def headers(self):
        return {'Authorization': "Bearer {}".format(self.bearer_token)}

    def get_oauth(self, oauth_token, oauth_token_secret):
        oauth = OAuth1(self.oauth_consumer_key, self.oauth_consumer_secret,
                       resource_owner_key=oauth_token, resource_owner_secret=oauth_token_secret)
        return oauth

    def post_for_request_token(self):

        params = {
            'oauth_callback': "oob",
            'oauth_consumer_key': self.oauth_consumer_key
        }

        response = requests.post(url=self.oauth_request_url, params=params, headers=self.headers)

        return response

    def post_for_access_token(self, pin, request_token, request_token_secret):

        params = {
            'oauth_token': request_token,
            'oauth_verifier': pin
        }

        # use the request token in oauth
        oauth = self.get_oauth(request_token, request_token_secret)
        response = requests.post(url=self.oauth_access_url, params=params, auth=oauth)

        return response

    def post_status_update(self, status, access_token, access_token_secret, media_ids=None, reply_id=None):
        params = {}

        if status:
            params['status'] = status

        if media_ids:
            params['media_ids'] = ','.join(media_ids)

        oauth = self.get_oauth(access_token, access_token_secret)
        response = requests.post(url=self.statuses_update_url, params=params, auth=oauth)

        return response

    def get_users_mentions(self, user_id, access_token=None, access_token_secret=None, tweet_fields=None,
                           expansions=None, media_fields=None):
        params = {}

        if isinstance(tweet_fields, list):
            params['tweet.fields'] = ','.join(tweet_fields)
        if isinstance(expansions, list):
            params['expansions'] = ','.join(expansions)
        if isinstance(media_fields, list):
            params['media.fields'] = ','.join(media_fields)

        statuses_mentions_timeline_url = self.users_mentions_url.format(user_id)

        # use the request token in oauth
        if (access_token is not None) & (access_token_secret is not None):
            oauth = self.get_oauth(access_token, access_token_secret)
            response = requests.get(url=statuses_mentions_timeline_url, params=params, auth=oauth)
        else:
            response = requests.get(url=statuses_mentions_timeline_url, params=params, headers=self.headers)

        return response.json()

    def get_tweets(self, ids: list, request_token=None, request_token_secret=None, tweet_fields=None,
                   expansions=None, media_fields=None):
        params = {
            'ids': ','.join(ids)
        }

        if isinstance(tweet_fields, list):
            params['tweet.fields'] = ','.join(tweet_fields)
        if isinstance(expansions, list):
            params['expansions'] = ','.join(expansions)
        if isinstance(media_fields, list):
            params['media_fields'] = ','.join(media_fields)

        get_tweet_url = self.get_tweets_url

        # use the request token in oauth
        if request_token & request_token_secret:
            oauth = self.get_oauth(request_token, request_token_secret)
            response = requests.get(url=statuses_mentions_timeline_url, params=params, auth=oauth)
        else:
            response = requests.get(url=statuses_mentions_timeline_url, params=params, headers=self.headers)

    class MediaUpload:
        def __init__(self, media_upload_url, oauth, media):
            self.media_upload_url = media_upload_url
            self.oauth = oauth
            self.media = media

            self.total_bytes = media.total_bytes
            self.media_type = 'image/png'
            self.media_category = 'TweetImage'

        def upload_init(self):
            '''
            Initializes Upload
            '''
            print('INIT')

            request_data = {
                'command': 'INIT',
                'media_type': self.media_type,
                'total_bytes': self.total_bytes,
                'media_category': self.media_category
            }

            req = requests.post(url=self.media_upload_url, data=request_data, auth=self.oauth)
            media_id = req.json()['media_id']

            self.media_id = media_id

            print('Media ID: %s' % str(media_id))

        def upload_append(self):
            '''
            Uploads media in chunks and appends to chunks uploaded
            '''
            segment_id = 0
            bytes_sent = 0

            while bytes_sent < self.total_bytes:
                chunk = self.media.read(4 * 1024 * 1024)

                print('APPEND')

                request_data = {
                    'command': 'APPEND',
                    'media_id': self.media_id,
                    'segment_index': segment_id
                }

                files = {
                    'media': chunk
                }

                req = requests.post(url=self.media_upload_url, data=request_data, files=files, auth=self.oauth)

                segment_id = segment_id + 1
                bytes_sent = self.media.tell()

                print('%s of %s bytes uploaded' % (str(bytes_sent), str(self.total_bytes)))

            print('Upload chunks complete.')

        def upload_finalize(self):
            '''
            Finalizes uploads and starts video processing
            '''
            print('FINALIZE')

            request_data = {
                'command': 'FINALIZE',
                'media_id': self.media_id
            }

            req = requests.post(url=self.media_upload_url, data=request_data, auth=self.oauth)
            print(req.json())

            processing_info = req.json().get('processing_info', None)
            self.check_status(processing_info)

        def check_status(self, processing_info):
            '''
            Checks video processing status
            '''
            if processing_info is None:
                return

            state = processing_info['state']

            print('Media processing status is %s ' % state)

            if state == u'succeeded':
                print('Upload succeeded')
                return

            if state == u'failed':
                print('Upload failed')
                return

            check_after_secs = processing_info['check_after_secs']

            print('Checking after %s seconds' % str(check_after_secs))
            time.sleep(check_after_secs)

            print('STATUS')

            request_params = {
                'command': 'STATUS',
                'media_id': self.media_id
            }

            req = requests.get(url=self.media_upload_url, params=request_params, auth=self.oauth)

            processing_info = req.json().get('processing_info', None)
            self.check_status(processing_info)

    def post_media_upload(self, media, access_token, access_token_secret):
        oauth = self.get_oauth(access_token, access_token_secret)
        media_upload = self.MediaUpload(self.media_upload_url, oauth, media)

        media_upload.upload_init()
        media_upload.upload_append()
        media_upload.upload_finalize()

        return media_upload.media_id

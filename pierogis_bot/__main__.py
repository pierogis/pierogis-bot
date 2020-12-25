import os

from .twitter import Twitter

if __name__ == '__main__':
    # get application credentials
    bearer_token = os.getenv('BEARER_TOKEN')
    oauth_consumer_key = os.getenv('OAUTH_CONSUMER_KEY')
    oauth_consumer_secret = os.getenv('OAUTH_CONSUMER_SECRET')

    # put these credentials into an api
    api = Twitter(bearer_token, oauth_consumer_key, oauth_consumer_secret)

    # leg 1 of Oauth. Get a request token and secret from twitter
    request_token_response = api.post_for_request_token()

    body = request_token_response.text.split('&')

    request_token = body[0].split('=')[1]
    request_token_secret = body[1].split('=')[1]

    # leg 2 of Oauth. Redirect user to authorize with that new token
    print("Redirect account to be controlled to:")
    print("https://api.twitter.com/oauth/authorize?oauth_token={}".format(request_token))

    # enter the pin from the user account
    print()
    pin = input("Enter the pin:")

    # now get an access token with the agreed upon request token
    api.oauth_access_token = request_token
    api.oauth_access_token_secret = request_token_secret
    access_token_response = api.post_for_access_token(pin)

    body = access_token_response.text.split('&')

    # different from above
    access_token = body[0].split('=')[1]
    access_token_secret = body[1].split('=')[1]
    user_id = body[2].split('=')[1]
    screen_name = body[3].split('=')[1]

    # store these in keys.yml
    print()
    print("Store these in keys.yml")
    print("accessToken: " + access_token)
    print("accessTokenSecret: " + access_token_secret)

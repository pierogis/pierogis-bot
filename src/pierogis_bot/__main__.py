import argparse
import os

from .serverless import send_orders

from .twitter import Twitter
from .utils import load_env, load_env_bot


def grant_account_access():
    """
    Performs 3 step oauth verification for an account
    Displays the access token and access token secret for that acct
    :return:
    """
    load_env()

    # get application credentials
    bearer_token = os.getenv('BEARER_TOKEN')
    oauth_consumer_key = os.getenv('OAUTH_CONSUMER_KEY')
    oauth_consumer_secret = os.getenv('OAUTH_CONSUMER_SECRET')

    # put these credentials into an api
    twitter = Twitter(bearer_token, oauth_consumer_key, oauth_consumer_secret)

    # leg 1 of Oauth. Get a request token and secret from twitter
    request_token_response = twitter.post_for_request_token()

    body = request_token_response.text.split('&')

    request_token = body[0].split('=')[1]
    request_token_secret = body[1].split('=')[1]

    # leg 2 of Oauth. Redirect user to authorize with that new token
    print()
    print("Redirect account to be controlled to:")
    print("https://api.twitter.com/oauth/authorize?oauth_token={}".format(request_token))

    # enter the pin from the user account
    print()
    pin = input("Enter the pin:")

    # now get an access token with the agreed upon request token
    access_token_response = twitter.post_for_access_token(pin, request_token, request_token_secret)

    body = access_token_response.text.split('&')

    # different from above
    access_token = body[0].split('=')[1]
    access_token_secret = body[1].split('=')[1]
    user_id = body[2].split('=')[1]

    print()
    print("Store these in config.{stage}.yml")
    print("ACCESS_TOKEN: " + access_token)
    print("ACCESS_TOKEN_SECRET: " + access_token_secret)
    print("USER_ID: " + user_id)


def make_reply(id, recipe_path, stage):
    bot = load_env_bot(stage)

    with open(recipe_path, 'r') as file:
        recipe = file.read()

    orders = bot.get_id_orders([id], recipe)

    send_orders(orders)


def main():
    """
    Manually invoke lambda handler functions and meta scripts
    :return:
    """
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers()

    # grant access to an account (get access token, secret)
    access_parser = subparsers.add_parser('access')
    access_parser.set_defaults(action=grant_account_access)

    # custom reply to id
    reply_parser = subparsers.add_parser('reply')
    reply_parser.set_defaults(action=make_reply)
    reply_parser.add_argument('-r', '--recipe_path', required=True, type=str, help='Path to the recipe file to use')
    reply_parser.add_argument('-s', '--stage', default='dev', type=str)
    reply_parser.add_argument('id', type=str, help='Tweet IDs to reply to')

    # both options funnel through this
    parsed = parser.parse_args()
    parsed_vars = vars(parsed)
    action = parsed_vars.pop('action')
    # call the func member of the parsed (set by default)
    action(**parsed_vars)


if __name__ == '__main__':
    main()

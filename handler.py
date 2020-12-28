import json
import os

import boto3
from boto3.dynamodb.conditions import Key
from dotenv import load_dotenv

from pierogis_bot import Bot

print('Select function to test')

load_dotenv('.env')

oauth_consumer_key = os.getenv('OAUTH_CONSUMER_KEY')
oauth_consumer_secret = os.getenv('OAUTH_CONSUMER_SECRET')
bearer_token = os.getenv('BEARER_TOKEN')

oauth_access_token = os.getenv('OAUTH_ACCESS_TOKEN')
oauth_access_token_secret = os.getenv('OAUTH_ACCESS_TOKEN_SECRET')

chef_arn = os.getenv('MEAL_CHEF_ARN')
orders_bucket_name = os.getenv('ORDERS_BUCKET')
user_id = os.getenv('USER_ID')

bot = Bot(
    bearer_token, oauth_consumer_key, oauth_consumer_secret, orders_bucket_name,
    oauth_access_token=oauth_access_token, oauth_access_token_secret=oauth_access_token_secret,
    chef_arn=chef_arn, user_id=user_id
)

sfn = boto3.client('stepfunctions')
ssm = boto3.client('ssm')


def poll_mentions(event, context):
    # get the last tweet processed from parameter store
    # since_id = ssm.get_parameter(Name='sinceId')
    # use the bot to poll the twitter api
    orders = bot.get_orders(0)

    tweet_id = None
    # recipe, ingredients, seasons, and urls in dict
    for order in orders:
        try:
            sfn.start_execution(
                stateMachineArn=chef_arn,
                input=json.dumps(order)
            )
        except:
            pass
        finally:
            order_id = order['orderId']

    if tweet_id is not None:
        # update the since id
        ssm.put_parameter(
            Name='sinceId',
            Value=str(tweet_id),
            Overwrite=True
        )


def download_ingredients(event, context):
    records = event['Records']
    for record in records:
        body = json.loads(record['body'])

        meal_id = str(body['mealId'])
        urls = body['urls']

        keys = bot.download_ingredients(meal_id, urls)
        task_token = body.get('taskToken')
        if task_token is not None:
            sfn.send_task_success(
                taskToken=task_token,
                output=json.dumps(keys)
            )


def cook_dishes(event, context):
    records = event['Records']
    for record in records:
        body = json.loads(record['body'])

        order_id = body['orderId']
        ingredients = body['ingredients']
        recipe = body['recipe']
        keys = body['keys']

        output_key = bot.cook_dish(order_id, ingredients, recipe, keys)
        task_token = body.get('taskToken')
        if task_token is not None:
            sfn.send_task_success(
                taskToken=task_token,
                output=json.dumps(output_key)
            )


def reply_tweets(event, context):
    records = event['Records']
    for record in records:
        body = json.loads(record['body'])
        keys = body['keys']
        meal_id = str(body['mealId'])
        username = body['username']

        bot.reply_tweet(keys, meal_id, username)

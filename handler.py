import json
import os

import boto3
from dotenv import load_dotenv

from pierogis_bot import Bot

print('Select function to test')

load_dotenv('.env')

oauth_consumer_key = os.getenv('OAUTH_CONSUMER_KEY')
oauth_consumer_secret = os.getenv('OAUTH_CONSUMER_SECRET')
bearer_token = os.getenv('BEARER_TOKEN')

oauth_access_token = os.getenv('OAUTH_ACCESS_TOKEN')
oauth_access_token_secret = os.getenv('OAUTH_ACCESS_TOKEN_SECRET')

meal_chef_arn = os.getenv('MEAL_CHEF_ARN')
meal_requests_bucket_name = os.getenv('MEAL_REQUESTS_BUCKET')
user_id = os.getenv('USER_ID')

bot = Bot(
    bearer_token, oauth_consumer_key, oauth_consumer_secret, meal_requests_bucket_name,
    oauth_access_token=oauth_access_token, oauth_access_token_secret=oauth_access_token_secret,
    meal_chef_arn=meal_chef_arn, user_id=user_id
)

sfn = boto3.client('stepfunctions')


def poll_mentions(event, context):
    meal_inputs = bot.poll_mentions()

    for meal_input in meal_inputs:
        sfn.start_execution(
            stateMachineArn=meal_chef_arn,
            input=json.dumps(meal_input)
        )


def download_ingredients(event, context):
    records = event['Records']
    for record in records:
        body = json.loads(record['body'])

        meal_id = body['mealId']
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

        meal_id = body['mealId']
        ingredients = body['ingredients']
        recipe = body['recipe']
        keys = body['keys']

        output_key = bot.cook_dish(meal_id, ingredients, recipe, keys)
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
        meal_id = body['mealId']
        username = body['username']

        bot.reply_tweet(keys, meal_id, username)

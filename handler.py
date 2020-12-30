import json
import os

import boto3

from pierogis_bot import Bot

try:
    import yaml

    with open('config.yml') as file:
        config = yaml.load(file)

    for name, value in config['dev'].items():
        os.environ[name] = str(value)

except ImportError:
    dotenv = None

print('Select function to test')

oauth_consumer_key = os.getenv('OAUTH_CONSUMER_KEY')
oauth_consumer_secret = os.getenv('OAUTH_CONSUMER_SECRET')
bearer_token = os.getenv('BEARER_TOKEN')

oauth_access_token = os.getenv('OAUTH_ACCESS_TOKEN')
oauth_access_token_secret = os.getenv('OAUTH_ACCESS_TOKEN_SECRET')

kitchen_arn = os.getenv('KITCHEN_ARN')
orders_bucket_name = os.getenv('ORDERS_BUCKET')
user_id = os.getenv('USER_ID')

orders_table_name = os.getenv('ORDERS_TABLE')

bot = Bot(
    bearer_token, oauth_consumer_key, oauth_consumer_secret, orders_bucket_name,
    oauth_access_token=oauth_access_token, oauth_access_token_secret=oauth_access_token_secret,
    user_id=user_id
)

sfn = boto3.client('stepfunctions')
ssm = boto3.client('ssm')
ddb = boto3.resource('dynamodb')


def poll_mentions(event, context):
    # get the last tweet processed from parameter store
    parameter_response = ssm.get_parameter(Name='/pierogis/chef/sinceId')
    since_id = parameter_response['Parameter']['Value']
    # use the bot to poll the twitter api
    orders = bot.get_orders(since_id)
    # orders = bot.get_orders('1343753267034124289')

    tweet_id = None
    orders_table = ddb.Table(orders_table_name)
    with orders_table.batch_writer() as batch:
        for order in orders:
            tweet_id = order.pop('tweet_id')
            author_id = order.pop('author_id')
            order['replyType'] = 'tweet'

            batch.put_item(
                Item={
                    'orderId': order['orderId'],
                    'replyType': order['replyType'],
                    'tweetId': tweet_id,
                    'authorId': author_id
                }
            )

            sfn.start_execution(
                stateMachineArn=kitchen_arn,
                input=json.dumps(order)
            )

    if tweet_id is not None:
        # update the since id
        ssm.put_parameter(
            Name='/pierogis/chef/sinceId',
            Value=str(tweet_id),
            Overwrite=True,
            Type='String'
        )


def download_ingredients(event, context):
    records = event['Records']
    for record in records:
        body = json.loads(record['body'])

        order_id = str(body['orderId'])
        file_links = body['fileLinks']

        file_links = bot.download_ingredients(order_id, file_links)
        task_token = body.get('taskToken')
        if task_token is not None:
            sfn.send_task_success(
                taskToken=task_token,
                output=json.dumps(file_links)
            )


def cook_dishes(event, context):
    records = event['Records']
    for record in records:
        body = json.loads(record['body'])

        order_id = body['orderId']
        ingredient_descs = body['ingredients']
        seasoning_links = body['seasoningLinks']
        recipe_orders = body['recipes']
        file_links = body['fileLinks']

        output_key = bot.cook_dish(order_id, ingredient_descs, seasoning_links, recipe_orders, file_links)
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
        order_id = str(body['orderId'])
        reply_type = body['replyType']

        if reply_type == 'tweet':
            orders_table = ddb.Table(orders_table_name)
            response = orders_table.get_item(
                Key={
                    'orderId': order_id,
                    'replyType': reply_type
                },
                AttributesToGet=[
                    'authorId',
                    'tweetId'
                ],
            )

            author_id = response['Item']['authorId']
            tweet_id = response['Item']['tweetId']

            bot.reply_tweet(tweet_id, author_id, keys)

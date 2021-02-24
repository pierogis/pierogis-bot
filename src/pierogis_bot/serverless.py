import argparse
import io
import json
import os

import boto3
import requests
from pyrogis.chef import DishDescription

from .bot import Bot
from pyrogis import Kitchen
from .utils import load_env_bot

bot = load_env_bot()


# sqs = boto3.resource('sqs')

def send_orders(orders):
    """
    Send a set of order description to the kitchen state machine

    :return:
    """
    kitchen_arn = os.getenv('KITCHEN_ARN')
    orders_table_name = os.getenv('ORDERS_TABLE')

    ddb = boto3.resource('dynamodb')
    orders_table = ddb.Table(orders_table_name)

    sfn = boto3.client('stepfunctions')

    tweet_id = None
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

    return tweet_id


def poll_mentions(event, context):
    # get the last tweet processed from parameter store
    ssm = boto3.client('ssm')
    parameter_response = ssm.get_parameter(Name='/pierogis/chef/sinceId')
    since_id = parameter_response['Parameter']['Value']
    # use the bot to poll the twitter api
    orders = bot.get_mention_orders(since_id)

    since_id = send_orders(orders)

    if since_id is not None:
        # update the since id
        ssm.put_parameter(
            Name='/pierogis/chef/sinceId',
            Value=str(since_id),
            Overwrite=True,
            Type='String'
        )


def download_ingredients(event, context):
    orders_bucket_name = os.environ['ORDERS_BUCKET']

    s3 = boto3.resource('s3')
    orders_bucket = s3.Bucket(orders_bucket_name)

    records = event['Records']
    for record in records:
        body = record['body']
        if isinstance(body, str):
            body = json.loads(body)

        order_id = str(body['orderId'])
        file_links = body['fileLinks']

        i = 0
        for file_uuid, url in file_links.items():
            extension = url.split('.')[-1]
            object_name = '/'.join(['input_media', str(order_id), str(i) + '.' + extension])

            response = requests.get(url, stream=True)

            with io.BytesIO(response.content) as file:
                orders_bucket.upload_fileobj(file, object_name)

            file_links[file_uuid] = object_name

            i += 1

        sfn = boto3.client('stepfunctions')

        task_token = body.get('taskToken')
        if task_token is not None:
            sfn.send_task_success(
                taskToken=task_token,
                output=json.dumps(file_links)
            )


def cook_dishes(event, context):
    orders_bucket_name = os.environ['ORDERS_BUCKET']

    s3 = boto3.resource('s3')
    orders_bucket = s3.Bucket(orders_bucket_name)

    dish_descs = {}

    records = event['Records']
    for record in records:
        body = record['body']
        if isinstance(body, str):
            body = json.loads(body)

        order_id = body['orderId']
        ingredients = body['ingredients']
        seasoning_links = body['seasoningLinks']
        dish = body['dish']
        files = body['files']
        pierogis = body['pierogis']

        dish_description = DishDescription(
            ingredients=ingredients,
            pierogis=pierogis,
            files=files,
            dish=dish,
            seasoning_links=seasoning_links
        )

        dish_descs[order_id] = dish_description

        Kitchen()

        for ingredient_uuid, s3_key in files.items():
            path = '/tmp/' + order_id + '-' + s3_key.split('/')[-1]
            orders_bucket.download_file(s3_key, path)
            files[ingredient_uuid] = path

    kitchen = Kitchen()

    cooked_dishes = kitchen.cook_dishes(dish_descs)
    for dish in cooked_dishes:
        output_filename = order_id + '.png'
        output_key = '/'.join(['output_media', output_filename])
        output_path = '/'.join(['/tmp', output_filename])

        dish.save(output_path)
        orders_bucket.upload_file(output_path, output_key)

        task_token = body.get('taskToken')
        if task_token is not None:
            sfn = boto3.client('stepfunctions')
            sfn.send_task_success(
                taskToken=task_token,
                output=json.dumps(output_key)
            )


def reply_tweets(event, context):
    orders_bucket_name = os.environ['ORDERS_BUCKET']
    orders_table_name = os.environ['ORDERS_TABLE']

    ddb = boto3.resource('dynamodb')
    orders_table = ddb.Table(orders_table_name)

    s3 = boto3.resource('s3')
    orders_bucket = s3.Bucket(orders_bucket_name)

    records = event['Records']
    for record in records:
        body = record['body']
        if isinstance(body, str):
            body = json.loads(body)
        keys = body['keys']
        order_id = str(body['orderId'])
        reply_type = body['replyType']

        if reply_type == 'tweet':
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

            paths = []

            for key in keys:
                file_object = orders_bucket.Object(key)
                path = '/tmp/' + key.split('/')[-1]
                file_object.download_file(path)

                paths.append(path)

            bot.reply_tweet(tweet_id, author_id, paths)

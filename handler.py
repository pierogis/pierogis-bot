from pierogis_bot import serverless


def call_poll_mentions(event, context):
    serverless.poll_mentions(event, context)


def call_download_ingredients(event, context):
    serverless.download_ingredients(event, context)


def call_cook_dishes(event, context):
    serverless.cook_dishes(event, context)


def call_reply_tweets(event, context):
    serverless.reply_tweets(event, context)

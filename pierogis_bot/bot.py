

class Bot:
    def poll_mentions(self):
        for batch in search_batches():
            LAMBDA.invoke(
                FunctionName=TWEET_PROCESSOR_FUNCTION_NAME,
                InvocationType='Event',
                Payload=json.dumps(batch)
            )


    def search_batches():
        since_id = None
        if STREAM_MODE_ENABLED:
            since_id = checkpoint.last_id()

        tweets = []
        while True:
            result = twitter_proxy.search(SEARCH_TEXT, since_id)
            if not result['statuses']:
                # no more results
                break

            tweets = result['statuses']
            size = len(tweets)
            for i in range(0, size, BATCH_SIZE):
                yield tweets[i:min(i + BATCH_SIZE, size)]
            since_id = result['search_metadata']['max_id']

            if STREAM_MODE_ENABLED:
                checkpoint.update(since_id)
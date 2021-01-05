import os

from .bot import Bot


def load_env(stage='dev'):
    try:
        import yaml

        with open('config.yml') as file:
            config = yaml.load(file)

        for name, value in config[stage].items():
            os.environ[name] = str(value)

    except ImportError:
        print('Install pyaml to use a yaml config file')


def load_env_bot(stage='dev'):
    load_env(stage)

    oauth_consumer_key = os.getenv('OAUTH_CONSUMER_KEY')
    oauth_consumer_secret = os.getenv('OAUTH_CONSUMER_SECRET')
    bearer_token = os.getenv('BEARER_TOKEN')

    oauth_access_token = os.getenv('OAUTH_ACCESS_TOKEN')
    oauth_access_token_secret = os.getenv('OAUTH_ACCESS_TOKEN_SECRET')
    user_id = os.getenv('USER_ID')

    # initiate shared bot
    bot = Bot(
        bearer_token, oauth_consumer_key, oauth_consumer_secret,
        oauth_access_token=oauth_access_token, oauth_access_token_secret=oauth_access_token_secret,
        user_id=user_id
    )

    return bot

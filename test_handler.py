import pytest
from dotenv import load_dotenv

from handler import schedule_tweet

load_dotenv("./.env")


@pytest.fixture()
def event():
    '''Slack message'''
    pass


@pytest.fixture()
def context():
    '''Slack message schema'''
    pass


def test_schedule_tweet(event, context):
    schedule_tweet(event, context)
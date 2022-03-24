import json

from mongo_utils import db_connection
from utils import background, run_sessions
from kafka import KafkaConsumer
from dotenv import dotenv_values


@background
def consume_data(market):
    topic = market
    config = dotenv_values(".env")
    consumer = KafkaConsumer(topic,
                             bootstrap_servers=[f"{config['KAFKA_HOST']}:{config['KAFKA_PORT']}"],
                             auto_offset_reset='latest',
                             enable_auto_commit=True,
                             )
    sessions_db = db_connection('larry_sessions')
    for message in consumer:
        data = json.loads(message.value)
        run_sessions(sessions_db, market, data)


def consume_back_testing_data(market):
    topic = market + '_B'
    config = dotenv_values(".env")
    consumer = KafkaConsumer(topic,
                             bootstrap_servers=[f"{config['KAFKA_HOST']}:{config['KAFKA_PORT']}"],
                             auto_offset_reset='latest',
                             enable_auto_commit=True,
                             )
    sessions_db = db_connection('larry_sessions_bt')
    for message in consumer:
        data = json.loads(message.value)
        run_sessions(sessions_db, market, data, bt=True)


def start_consuming():
    config = dotenv_values(".env")
    markets = config['SUBSCRIPTION_LIST'].split(',')
    for market in markets:
        market = market.upper()
        if bool(config['BACK_TEST']):
            consume_back_testing_data(market)
        else:
            consume_data(market)



import json

from mongo_utils import db_connection
from utils import background, run_sessions
from kafka import KafkaConsumer
from dotenv import dotenv_values


@background
def consume_data(market):
    config = dotenv_values(".env")
    consumer = KafkaConsumer(market,
                             bootstrap_servers=[f"{config['KAFKA_HOST']}:{config['KAFKA_PORT']}"],
                             auto_offset_reset='latest',
                             enable_auto_commit=True,
                             )
    sessions_db = db_connection('larry_sessions')
    for message in consumer:
        data = json.loads(message.value)
        run_sessions(sessions_db, market, data)


def start_consuming():
    config = dotenv_values(".env")
    markets = config['SUBSCRIPTION_LIST'].split(',')
    for market in markets:
        consume_data(market.upper())

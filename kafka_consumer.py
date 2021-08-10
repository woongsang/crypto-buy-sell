from mongo_utils import db_connection
from utils import background, check_close_position, check_open_position
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
    for data in consumer:
        check_open_position(sessions_db, market, data, position=1)
        check_open_position(sessions_db, market, data, position=-1)
        check_close_position(sessions_db, market, data)


def start_consuming():
    config = dotenv_values(".env")
    markets = config['SUBSCRIPTION_LIST'].split(',')
    for market in markets:
        consume_data(market.upper())

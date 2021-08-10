import time

from dotenv import dotenv_values
from pymongo import MongoClient

config = dotenv_values(".env")


def db_connection(db_name):
    mongo_client = MongoClient(f"{config['MONGO_DB_HOST']}:{config['MONGO_DB_PORT']}/",
                               username=config['MONGO_DB_USER'],
                               password=config['MONGO_DB_PASSWORD'])
    db = mongo_client[db_name]
    return db


def retrieve_mongo_data(db, cycle_hours):
    timestamp = time.time() * 1000
    time_start = timestamp - cycle_hours * 60 * 60 * 1000
    results = db.find({'timestamp': {'$gte': time_start}})
    timestamp_list = []
    price_list = []
    for result in results:
        timestamp_list.append(result['timestamp'])
        price_list.append(result['price'])

    return timestamp_list, price_list

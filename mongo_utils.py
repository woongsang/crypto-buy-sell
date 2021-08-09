from dotenv import dotenv_values
from pymongo import MongoClient

config = dotenv_values(".env")


def db_connection(db_name):
    mongo_client = MongoClient(f"{config['MONGO_DB_HOST']}:{config['MONGO_DB_PORT']}/",
                               username=config['MONGO_DB_USER'],
                               password=config['MONGO_DB_PASSWORD'])
    db = mongo_client[db_name]
    return db



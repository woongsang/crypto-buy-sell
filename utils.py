import asyncio

from bson import ObjectId

import binance_api
from mongo_utils import db_connection


def background(f):
    def wrapped(*args, **kwargs):
        return asyncio.get_event_loop().run_in_executor(None, f, *args, **kwargs)

    return wrapped


@background
def open_position(session, current_price):
    accounts_db = db_connection('exchange_accounts')
    account = accounts_db[session['market']].find_one({'_id': ObjectId(session['exchange_account_id'])})
    binance_api.open_position(account, session, current_price)


def reached_stop_loss(current_price):
    # Todo: check if the balance has reached at stop loss
    return False


def check_open_position(sessions_db, market, data, position):
    sign = '$lte' if position == 1 else '$gte'
    sessions = sessions_db[market].find({'close_timestamp': {'$eq': None},
                                         'position': {'$eq': 1},
                                         'target_entry_price': {sign: data['price']}
                                         })
    for session in sessions:
        open_position(session, data['price'])


def check_close_position(sessions_db, market, data):
    open_sessions = sessions_db[market].find({'close_timestamp': {'$ne': None}})

    remove_list = []
    for session in open_sessions:
        if data['timestamp'] >= session['close_timestamp'] or reached_stop_loss(data['price']):
            binance_api.close_position()
            remove_list.append(session['_id'])

    sessions_db[market].delete_many({'_id': {'$in': remove_list}})

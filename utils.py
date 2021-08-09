import asyncio

from binance_api import open_position_limit_price, close_position
from mongo_utils import db_connection


def background(f):
    def wrapped(*args, **kwargs):
        return asyncio.get_event_loop().run_in_executor(None, f, *args, **kwargs)

    return wrapped


@background
def open_position(session, current_price):
    accounts_db = db_connection('exchange_accounts')
    account = accounts_db[session['market']].find_one({'_id': session['exchange_account_id']})
    api_key = account['api_key']
    secret_key = account['secret_key']
    limit_price = current_price * (1 + session['position'] * session['slippage_percentage'] / 100)
    buy_percentage = session['buy_percentage']
    position = 'long' if session['position'] == 1 else 'short'
    market = session['market']

    open_position_limit_price()


def reached_stop_loss():
    # Todo: check if the balance has reached at stop loss
    return False


def check_close_position(sessions_db, market, current_price, current_timestamp):
    in_position_sessions = sessions_db[market].find({'close_timestamp': {'$ne': None}})

    remove_list = []
    for session in in_position_sessions:
        if current_timestamp >= session['close_timestamp'] or reached_stop_loss():
            close_position()
            remove_list.append(session['_id'])

    sessions_db[market].delete_many({'_id': {'$in': remove_list}})

import asyncio
from datetime import datetime

import requests
from bson import ObjectId

import binance_api
from buy_strategies import volatility_breakout_price
from mongo_utils import db_connection, retrieve_mongo_data


def initialize_larry_session(larry_session):
    mongo_timestamps, mongo_prices = retrieve_mongo_data(db_connection('data')[larry_session['market']],
                                                         larry_session['cycle_hours'])
    larry_session['long_target_price'], larry_session['short_target_price'] = \
        volatility_breakout_price(
            prev_high=max(mongo_prices),
            prev_low=min(mongo_prices),
            prev_price=mongo_prices[-1],
            x=larry_session['x'])
    larry_session['update_timestamp'] = mongo_timestamps[-1]
    larry_session['reset_timestamp'] = mongo_timestamps[-1] + larry_session['cycle_hours'] * 60 * 60 * 1000
    db = db_connection('larry_sessions')
    db[larry_session['market']].insert_one(larry_session)


def reset_larry_session(session, data):
    long_target_price = None
    short_target_price = None
    position = 0
    if data['timestamp'] >= session['reset_timestamp']:
        position = None
        db = db_connection('data')[session['market']]
        mongo_timestamps, mongo_prices = retrieve_mongo_data(db, session['cycle_hours'])
        long_target_price, short_target_price = volatility_breakout_price(
            prev_high=max(mongo_prices),
            prev_low=min(mongo_prices),
            prev_price=mongo_prices[-1],
            x=session['x'])

    session_db = db_connection('larry_sessions')
    content = {'coin_amount': None,
               'update_timestamp': data['timestamp'],
               'close_timestamp': None,
               'sl_tp_price': None,
               'position': position,
               'long_target_price': long_target_price,
               'short_target_price': short_target_price}

    if position is None:
        content['reset_timestamp'] += session['cycle_hours'] * 60 * 60 * 1000

    session_db[session['market']].find_one_and_update(
        {'_id': session['_id']},
        {'$set': content}
    )


def background(f):
    def wrapped(*args, **kwargs):
        return asyncio.get_event_loop().run_in_executor(None, f, *args, **kwargs)

    return wrapped


# @background
def update_after_open_position(session, data, position, order):
    session_db = db_connection('larry_sessions')
    content = {'coin_amount': order['amount'],
               'update_timestamp': data['timestamp'],
               'close_timestamp': data['timestamp'] + session['in_position_hours'],
               'sl_tp_price': order['price'] * (1 - position * session['sl_tp_percentage'] / 100)}
    session_db[session['market']].find_one_and_update(
        {'_id': session['_id']},
        {'$set': content}
    )

    accounts_db = db_connection('exchange_accounts')
    account = accounts_db[session['exchange']].find_one({'_id': ObjectId(session['exchange_account_id'])})

    content['position'] = session['position']
    content['market'] = session['market']
    content['price'] = data['price']
    content['update_timestamp'] = str(datetime.utcfromtimestamp(content['update_timestamp']/1000))
    content['close_timestamp'] = str(datetime.utcfromtimestamp(content['close_timestamp'] / 1000))
    send_message_to_slack(account['slack_url'], str(content))
    send_message_to_slack(account['slack_url'], str(order))


@background
def open_position(session, data, position):
    accounts_db = db_connection('exchange_accounts')
    account = accounts_db[session['exchange']].find_one({'_id': ObjectId(session['exchange_account_id'])})
    order = binance_api.open_position(account, session, data['price'], position)
    # Todo: check if the order was made
    update_after_open_position(session, data, position, order)


def reached_stop_loss_take_profit(session, current_price):
    if session['position'] == 1 and current_price <= session['sl_tp_price']:
        return True
    if session['position'] == -1 and current_price >= session['sl_tp_price']:
        return True

    return False


def check_open_position(sessions_db, market, data, position):
    if position == 1:
        sign = '$lte'
        target_entry_price = 'long_target_price'
    else:
        sign = '$gte'
        target_entry_price = 'short_target_price'
    sessions = sessions_db[market].find({'position': {'$eq': None},
                                         target_entry_price: {sign: data['price']}
                                         })
    for session in sessions:
        open_position(session, data, position)


def reached_close_timestamp(session, data):
    return session['close_timestamp'] is not None and data['timestamp'] >= session['close_timestamp']


@background
def close_position_session(session, data):
    close_timeout = reached_close_timestamp(session, data)
    sl_tp = reached_stop_loss_take_profit(session, data['price'])
    reset_timeout = data['timestamp'] >= session['reset_timestamp']
    order = None
    if close_timeout or sl_tp:
        accounts_db = db_connection('exchange_accounts')
        account = accounts_db[session['exchange']].find_one({'_id': ObjectId(session['exchange_account_id'])})
        order = binance_api.close_position(account, session)
        reset_larry_session(session, data)
        # remove_list.append(session['_id'])

    elif reset_timeout:
        reset_larry_session(session, data)

    content = {'close_timeout': close_timeout,
               'sl_tp': sl_tp,
               'reset_timeout': reset_timeout,
               'time': datetime.utcfromtimestamp(data['timestamp']/1000),
               'market': session['market'],
               'price': data['price']}

    accounts_db = db_connection('exchange_accounts')
    account = accounts_db[session['exchange']].find_one({'_id': ObjectId(session['exchange_account_id'])})
    send_message_to_slack(account['slack_url'], str(content))
    if order is not None:
        send_message_to_slack(account['slack_url'], str(order))


def check_close_position(sessions_db, market, data):
    # sign = '$lte' if position == 1 else '$gte'
    #
    # sessions = sessions_db[market].find({'position': {'$in': [0, 1]},
    #                                      '$or': [
    #                                          {'close_timestamp': {'$lte': data['timestamp']}},
    #                                          {'sl_tp_price': {sign: data['price']}}
    #                                      ],
    #                                      })
    sessions = sessions_db[market].find({'position': {'$in': [-1, 1]}})

    # remove_list = []
    for session in sessions:
        close_position_session(session, data)
    # sessions_db[market].delete_many({'_id': {'$in': remove_list}})


def send_message_to_slack(url, text):
    payload = {'text': text}
    requests.post(url, json=payload)

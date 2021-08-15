import asyncio
from datetime import datetime

import requests
from bson import ObjectId

import binance_api
from buy_strategies import volatility_breakout_price
from mongo_utils import db_connection, retrieve_mongo_data


def update_stop_loss(session, data):
    pass


def timeout_update_session(session, data):
    if data['timestamp'] < session['sliding_timestamp']:
        return False

    update_sliding_data(session, data['timestamp'])
    return True


def run_sessions(sessions_db, market, data):
    sessions = sessions_db[market].find()
    for session in sessions:
        if session['position'] is None:  # not holding any position
            open_position_session(session, data)
        elif session['position'] in [1, -1]:  # either long or short
            position_closed = close_position_session(session, data)
            if not position_closed:
                update_stop_loss(session, data)

        timeout_update_session(session, data)


def initialize_larry_session(session):
    db = db_connection('data')[session['market']]
    mongo_timestamps, mongo_prices = retrieve_mongo_data(db, session['cycle_hours'])
    long_target_price, short_target_price = get_target_prices(session, mongo_prices)

    session['long_target_price_dict'] = {str(mongo_timestamps[-1]): long_target_price}
    session['short_target_price_dict'] = {str(mongo_timestamps[-1]): short_target_price}

    session['sliding_timestamp'] = mongo_timestamps[-1] + session['sliding_hours'] * 60 * 60 * 1000

    db = db_connection('larry_sessions')

    db[session['market']].insert_one(session)


def get_target_prices(session, mongo_prices):
    sorted_prices = sorted(mongo_prices)
    return volatility_breakout_price(prev_high=sorted_prices[-100],
                                     prev_low=sorted_prices[100],
                                     prev_price=sum(mongo_prices[0:50]) / 50,
                                     x=session['x'])


def update_sliding_data(session, current_timestamp):
    db = db_connection('data')[session['market']]
    mongo_timestamps, mongo_prices = retrieve_mongo_data(db, session['cycle_hours'])
    long_target_price, short_target_price = get_target_prices(session, mongo_prices)

    new_sliding_timestamp = session['sliding_timestamp'] + session['sliding_hours'] * 60 * 60 * 1000

    for timestamp, target_price in session['long_target_price_dict'].items():
        if current_timestamp >= int(timestamp) + session['sliding_hours']:
            del session['long_target_price_dict'][timestamp]

    session['long_target_price_dict'][str(new_sliding_timestamp)] = long_target_price
    session['short_target_price_dict'][str(new_sliding_timestamp)] = short_target_price

    update_content = {'long_target_price_dict': session['long_target_price_dict'],
                      'short_target_price_dict': session['short_target_price_dict'],
                      'sliding_timestamp': new_sliding_timestamp}

    session_db = db_connection('larry_sessions')

    session_db[session['market']].find_one_and_update(
        {'_id': session['_id']},
        {'$set': update_content}
    )


def reset_larry_session(session):
    session_db = db_connection('larry_sessions')
    content = {'coin_amount': None,
               'close_timestamp': None,
               'stop_loss_price': None,
               'position': 0,
               }

    session_db[session['market']].find_one_and_update(
        {'_id': session['_id']},
        {'$set': content}
    )


def background(f):
    def wrapped(*args, **kwargs):
        return asyncio.get_event_loop().run_in_executor(None, f, *args, **kwargs)

    return wrapped


# @background
def update_after_open_position(session, data, position, order_id):
    accounts_db = db_connection('exchange_accounts')
    account = accounts_db[session['exchange']].find_one({'_id': ObjectId(session['exchange_account_id'])})

    order = binance_api.fetch_order(account, order_id, session)

    if order['remaining'] > 0.0:
        order = binance_api.cancel_order(account, order_id, session)
        if order['filled'] == 0:
            position = 0
    session_db = db_connection('larry_sessions')

    content = {'coin_amount': order['filled'],
               'close_timestamp': data['timestamp'] + session['in_position_hours'],
               'stop_loss_price':
                   float(order['info']['avgPrice']) * (1 - position * session['stop_loss_percentage'] / 100),
               'average_price': float(order['info']['avgPrice']),
               'position': position}
    session_db[session['market']].find_one_and_update(
        {'_id': session['_id']},
        {'$set': content}
    )

    content['position'] = session['position']
    content['market'] = session['market']
    content['price'] = data['price']
    content['close_timestamp'] = str(datetime.utcfromtimestamp(content['close_timestamp'] / 1000))
    send_message_to_slack(account['slack_url'], str(content))
    send_message_to_slack(account['slack_url'], str(order))


# def check_order(account, session, order):
#     if


def open_position(session, data, position):
    accounts_db = db_connection('exchange_accounts')
    account = accounts_db[session['exchange']].find_one({'_id': ObjectId(session['exchange_account_id'])})
    order = binance_api.open_position(account, session, data['price'], position)
    # check_order(account, session, order)
    return order


def reached_stop_loss(session, current_price):
    if session['position'] == 1 and current_price <= session['stop_loss_price']:
        return True
    if session['position'] == -1 and current_price >= session['stop_loss_price']:
        return True

    return False


def reached_target_price(session, data, position):
    key_list = []
    reached_target = False

    if position == 1:
        price_dict = session['long_target_price_dict']
    elif position == -1:
        price_dict = session['short_target_price_dict']
    else:
        raise KeyError("Wrong position value!")

    for timestamp, target_price in price_dict.items():
        key_list.append(timestamp)
        if (position == 1 and data['price'] >= target_price) or (position == -1 and data['price'] <= target_price):
            # open_position(session, data, position)
            reached_target = True
            break

    if not reached_target:
        return False

    if reached_target:
        for key in key_list:
            if key in price_dict:
                del price_dict[key]

    return reached_target


def open_position_session(session, data):
    if reached_target_price(session, data, 1):
        position = 1
        order = open_position(session, data, position)
    elif reached_target_price(session, data, -1):
        position = -1
        order = open_position(session, data, position)
    else:
        return False

    update_after_open_position(session, data, position, order['id'])
    return True


def reached_close_timestamp(session, data):
    return session['close_timestamp'] is not None and data['timestamp'] >= session['close_timestamp']


def close_position_session(session, data):
    close_timeout = reached_close_timestamp(session, data)
    stop_loss = reached_stop_loss(session, data['price'])

    if close_timeout:
        accounts_db = db_connection('exchange_accounts')
        account = accounts_db[session['exchange']].find_one({'_id': ObjectId(session['exchange_account_id'])})
        order = binance_api.close_position(account, session)
        reset_larry_session(session)

    elif stop_loss:
        accounts_db = db_connection('exchange_accounts')
        account = accounts_db[session['exchange']].find_one({'_id': ObjectId(session['exchange_account_id'])})
        order = binance_api.close_position(account, session)
        reset_larry_session(session)

    else:
        return False

    content = {'close_timeout': close_timeout,
               'stop_loss': stop_loss,
               'time': datetime.utcfromtimestamp(data['timestamp'] / 1000),
               'market': session['market'],
               'price': data['price']}

    accounts_db = db_connection('exchange_accounts')
    account = accounts_db[session['exchange']].find_one({'_id': ObjectId(session['exchange_account_id'])})
    send_message_to_slack(account['slack_url'], str(content))
    if order is not None:
        send_message_to_slack(account['slack_url'], str(order))

    return True


def send_message_to_slack(url, text):
    payload = {'text': text}
    requests.post(url, json=payload)

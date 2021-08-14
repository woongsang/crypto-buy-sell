import ccxt
from ccxt import ExchangeError


def get_future_api(api_key, secret_key):
    api = ccxt.binance(config={
        'apiKey': api_key,
        'secret': secret_key,
        'enableRateLimit': True,
        'options': {
            'defaultType': 'future',
            'adjustForTimeDifference': True
        }
    })
    return api


# @background
def open_position(account, session, current_price, position, currency='USDT', trade_type='limit'):
    api = get_future_api(account['api_key'], account['secret_key'])

    balance = api.fetch_partial_balance(currency)
    price = balance['total'] * session['entry_percentage'] / 100
    price = min(price, balance['free'])
    amount = price / current_price

    limit_price = current_price * (1 + position * session['slippage_percentage'] / 100)

    side = 'buy' if position == 1 else 'sell'
    symbol = session['market'].replace(currency, '') + '/' + currency

    api.set_leverage(symbol=symbol,
                     leverage=session['leverage_times'])
    order = None
    try:
        order = api.create_order(symbol=symbol,
                                 type=trade_type,
                                 side=side,
                                 amount=amount,
                                 price=limit_price,
                                 # params={"reduceOnly": True}
                                 )
    except ExchangeError as e:
        print(e)
    return order


# @background
def close_position(account, session, currency='USDT'):

    api = get_future_api(account['api_key'], account['secret_key'])

    side = 'buy' if session['position'] == -1 else 'sell'
    symbol = session['market'].replace(currency, '') + '/' + currency

    order = api.create_order(symbol=symbol,
                             type="MARKET",
                             side=side,
                             amount=session['coin_amount'],
                             params={"reduceOnly": True})
    return order


def fetch_order(account, order_id, session, currency='USDT'):
    symbol = session['market'].replace(currency, '') + '/' + currency
    api = get_future_api(account['api_key'], account['secret_key'])
    return api.fetch_order(order_id, symbol)


def cancel_order(account, order_id, session, currency='USDT'):
    symbol = session['market'].replace(currency, '') + '/' + currency
    api = get_future_api(account['api_key'], account['secret_key'])
    return api.cancel_order(order_id, symbol)

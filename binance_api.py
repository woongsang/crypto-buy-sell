import ccxt


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


def open_position(account, session, current_price, trade_type='limit'):
    api = get_future_api(account['api_key'], account['secret_key'])

    total_balance = api.fetch_total_balance()
    target_entry_amount = total_balance * session['entry_percentage'] / 100
    limit_price = current_price * (1 + session['position'] * session['slippage_percentage'] / 100)
    stop_loss_price = current_price * (1 - session['position'] * session['stop_loss_percentage'] / 100)
    params = {'stopPrice': stop_loss_price}
    # Todo: Apply stop-loss / take-profit when creating an order
    side = 'buy' if session['position'] == 1 else 'sell'

    api.set_leverage(symbol=session['market'],
                     leverage=session['leverage_times'])
    order = api.create_order(symbol=session['market'],
                             type=trade_type,
                             side=side,
                             amount=target_entry_amount,
                             price=limit_price)

    return order


def close_position(account, session):
    market = session['market']

    api = get_future_api(account['api_key'], account['secret_key'])
    side = 'buy' if session['position'] == -1 else 'sell'

    # Todo: how to determine the position amount? Doesn't it keep changing?
    order = api.create_order(symbol=market,
                             type="MARKET",
                             side=side,
                             amount=pos['positionAmt'],
                             params={"reduceOnly": True})
    pass

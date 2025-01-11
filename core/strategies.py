import api.fetch as api
import math

config = api.get_settings()


def strategy(candles):
    if candles['rsi'] <= 30.0:
        response = {'buy': True,
                    'price': candles['open'],
                    'amount': config['account']['baseOrderValue']}
    else:
        response = {'buy': False}
    return response
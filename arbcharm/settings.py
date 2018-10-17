# !/usr/bin/env python
__author__ = 'Rick Zhang'
__time__ = '2018/10/12'

import os

MODE = os.getenv('ARBCHARM_MODE', 'test')  # or prd

ARBITRAGE_OPPORTUNITY_RATE = 0.004

ARBCHARM_AMOUNT_MULTIPLIER = 0.01

CACHE_ORDER_ROW_LENGTH = 20

ARB_CONF = {
    'BTC/USDT': {
        'binance': {
            'apiKey': os.getenv('binance_apiKey', 'test'),
            'secret': os.getenv('binance_secret', 'test'),
            'min_amount': 0.002
        },
        'huobipro': {
            'apiKey': os.getenv('huobipro_apiKey', 'test'),
            'secret': os.getenv('huobipro_secret', 'test'),
            'min_amount': 0.002
        },
    }
}

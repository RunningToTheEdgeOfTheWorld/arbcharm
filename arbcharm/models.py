# !/usr/bin/env python
__author__ = 'Rick Zhang'
__time__ = '2018/10/12'

import asyncio
import time
from typing import Dict, List

import ccxt.async_support as ccxt
from arbcharm.tools import get_logger


class BaseExchange:
    def __init__(self, name, config: Dict):
        self.name = name
        self.logger = get_logger(self.name)
        self.ccxt_exchange = getattr(ccxt, self.name)(config)
        self._orderbook_d = {}
        self.alert_event_dict = {}  # sym: event

    def set_book(self, ob: "OrderBook"):
        if ob.symbol in self.alert_event_dict:
            self.alert_event_dict[ob.symbol].set()
        self._orderbook_d[ob.symbol] = ob

    def get_book(self, symbol) -> "OrderBook":
        return self._orderbook_d.get(symbol)

    def clear_book(self, symbol):
        self._orderbook_d[symbol] = None

    async def wait_book_update(self, symbol):
        event = self.alert_event_dict.get(symbol)
        if not event:
            self.alert_event_dict[symbol] = asyncio.Event()
        await self.alert_event_dict[symbol].wait()

    def reset_book_update(self, symbol):
        self.alert_event_dict[symbol].clear()

    async def set_orderbook_d(self, symbol):
        raise NotImplementedError()

    async def cancel_all(self):
        raise NotImplementedError()

    def __str__(self):
        return self.name


def _get_exchange_factory():

    single_instance = {}

    def _get_exchange(name, config) -> BaseExchange:
        if name not in single_instance:
            if name == 'bitfinex':
                from arbcharm.exchange_api.bitfinex import Bitfinex
                exc_cls = Bitfinex
            elif name == 'huobipro':
                from arbcharm.exchange_api.huobipro import HuoBiPro
                exc_cls = HuoBiPro
            elif name == 'binance':
                from arbcharm.exchange_api.binance import Binance
                exc_cls = Binance
            else:
                exc_cls = BaseExchange
            single_instance[name] = exc_cls(name, config)
        return single_instance[name]

    return _get_exchange


get_exchange = _get_exchange_factory()


class Trade:
    def __init__(
            self,
            *,
            bid_exc: BaseExchange,
            ask_exc: BaseExchange,
            bid_price,
            ask_price,
            amount
    ):
        """
        :param bid_exc: bid_price所属的交易所
        :param ask_exc: ask_price所属的交易所
        :param bid_price: 成交的orderbook买档价格
        :param ask_price: 成交的orderbook卖档价格
        :param amount: 成交量
        """
        assert bid_price >= ask_price
        self.bid_exc = bid_exc
        self.ask_exc = ask_exc
        self.bid_price = bid_price
        self.ask_price = ask_price
        self.amount = amount

    def __str__(self):
        return 'Trade:[{}]'.format(self.__dict__)

    def to_dict(self):
        return self.__dict__


class Order:
    SIDE_BUY = 'buy'
    SIDE_SELL = 'sell'

    def __init__(self, *, exc: BaseExchange, symbol, price, amount, side, otype='limit'):
        self.exc = exc
        assert side in (self.SIDE_SELL, self.SIDE_BUY)
        self.symbol = symbol
        self.side = side
        self.price = price
        self.amount = amount
        self.otype = otype

    def to_dict(self):
        return self.__dict__

    def __str__(self):
        return 'Order:[{}]'.format(self.to_dict())


class OrderRow:
    def __init__(self, *, price: float, amount: float, count: int):
        self.price = price
        self.count = count
        self.amount = amount


class OrderBook:
    def __init__(
            self,
            *,
            exchange: BaseExchange,
            symbol: str,
            asks: List[OrderRow],
            bids: List[OrderRow],
            timestamp: float
    ):
        self.exchange = exchange
        self.symbol = symbol
        self.asks = asks
        self.bids = bids
        self.timestamp = timestamp if timestamp else time.time()

    def remove_bad_price(self, price):
        self.asks = [row for row in self.asks if row.price >= price]
        self.bids = [row for row in self.bids if row.price <= price]

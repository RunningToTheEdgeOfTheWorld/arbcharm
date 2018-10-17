# !/usr/bin/env python
__author__ = 'Rick Zhang'
__time__ = '2018/10/12'

import asyncio
import json
import time

import websockets

from arbcharm.models import BaseExchange, OrderBook, OrderRow


class Binance(BaseExchange):
    """
    binance websockets doc:
    https://github.com/binance-exchange/binance-official-api-docs/blob/master/web-socket-streams.md
    """
    async def set_orderbook_d(self, symbol):
        """
        bitfinex websockets doc: https://docs.bitfinex.com/docs/ws-general
        """
        if symbol in self._orderbook_d:
            return
        self.clear_book(symbol)

        while True:
            try:
                await self._cache_book_ws(symbol)
            except websockets.exceptions.ConnectionClosed as e:
                self.logger.exception(error_class=e.__class__.__name__)  # TODO fix connection error
                await asyncio.sleep(10)
            except:  # pylint: disable=bare-except
                self.logger.exception()
                await asyncio.sleep(10)

    async def _cache_book_ws(self, symbol):
        __sym = symbol.replace('/', '').lower()
        stm_book = '{}@depth20'.format(__sym)
        stm_trade = '{}@aggTrade'.format(__sym)
        url = 'wss://stream.binance.com:9443/stream?streams={}/{}'.format(stm_book, stm_trade)

        async with websockets.connect(url) as ws:
            while True:
                msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=30))
                event = msg.get('stream')
                if event == stm_book:
                    self.deal_book_event(symbol, msg['data'])
                elif event == stm_trade:
                    self.deal_trade_event(symbol, msg['data'])

    def deal_book_event(self, symbol, data):
        """
        data:
        {
            'lastUpdateId': 265429175,
            'bids': [['6749.48000000', '0.14953300', []],...],
            'asks': [['6749.48000000', '0.14953300', []],...],
        }
        """
        ob = OrderBook(
            exchange=self,
            symbol=symbol,
            asks=[OrderRow(price=float(p), amount=float(a), count=1) for p, a, _ in data['asks']],
            bids=[OrderRow(price=float(p), amount=float(a), count=1) for p, a, _ in data['bids']],
            timestamp=time.time(),
        )
        self.set_book(ob)

    def deal_trade_event(self, symbol, data):
        """
        data:
        {
            'e': 'aggTrade',
            'E': 1539683812143,
            's': 'BTCUSDT',
            'a': 67071898,
            'p': '6754.35000000',
            'q': '0.22700000',
            'f': 75240975,
            'l': 75240975,
            'T': 1539683812141,
            'm': False,
            'M': True
        }
        """
        ob = self.get_book(symbol)
        if ob:
            ob.remove_bad_price(float(data['p']))

    async def cancel_all(self):
        pass


if __name__ == '__main__':
    ba = Binance('binance', {})
    lp = asyncio.get_event_loop()
    lp.run_until_complete(ba.set_orderbook_d('BTC/USDT'))

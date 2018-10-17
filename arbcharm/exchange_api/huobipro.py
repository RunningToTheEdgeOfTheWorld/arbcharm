# !/usr/bin/env python
__author__ = 'Rick Zhang'
__time__ = '2018/10/12'

import asyncio
import gzip
import json
import time

import websockets

from arbcharm.models import BaseExchange, OrderBook, OrderRow


class HuoBiPro(BaseExchange):
    async def set_orderbook_d(self, symbol):
        """
        huobipro websockets doc: https://github.com/huobiapi/API_Docs/wiki/WS_request
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
        url = 'wss://api.huobi.pro/ws'
        __sym = symbol.replace('/', '').lower()
        topic = 'market.{}.depth.step0'.format(__sym)
        async with websockets.connect(url) as ws:
            await self.send_data(ws, {'sub': topic, "freq-ms": 0})
            while True:
                data = self.decompress_msg(await asyncio.wait_for(ws.recv(), timeout=30))
                await self.data_handler(ws, symbol, data)

    async def data_handler(self, ws, symbol, data):
        if 'ping' in data:
            await self.send_data(ws, {'pong': int(time.time()*1000)})
            return
        elif 'status' in data:
            if data['status'] != 'ok':
                self.logger.error(data)
            return
        elif 'ch' in data:
            self.handle_book(symbol, data)
        else:
            self.logger.error(event='unhandle_data', data=data)

    def handle_book(self, symbol, data):
        asks = [OrderRow(price=p, amount=a, count=1) for p, a in data['tick']['asks']]
        bids = [OrderRow(price=p, amount=a, count=1) for p, a in data['tick']['bids']]
        timestamp = data['tick']['ts']/1000
        ob = OrderBook(exchange=self, symbol=symbol, asks=asks, bids=bids, timestamp=timestamp)
        self.set_book(ob)

    @staticmethod
    async def send_data(ws, data):
        await ws.send(json.dumps(data))

    @staticmethod
    def decompress_msg(msg):
        return json.loads(gzip.decompress(msg).decode())

    @staticmethod
    def compress_msg(msg):
        return gzip.compress(json.dumps(msg).encode())

    async def cancel_all(self):
        pass


if __name__ == '__main__':
    ba = HuoBiPro('huobipro', {})
    lp = asyncio.get_event_loop()
    lp.run_until_complete(ba.set_orderbook_d('BTC/USDT'))

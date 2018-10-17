# !/usr/bin/env python
__author__ = 'Rick Zhang'
__time__ = '2018/10/12'

import asyncio
import json
import time

import websockets

from arbcharm import errors, settings
from arbcharm.models import BaseExchange, OrderBook, OrderRow
from arbcharm.tools import bisect_right, rate_limit_generator


class Bitfinex(BaseExchange):
    """
    bitfinex websockets doc: https://docs.bitfinex.com/docs/ws-general
    """
    async def set_orderbook_d(self, symbol):
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
        # pylint: disable=too-many-locals, too-many-branches, too-many-statements
        __sym = symbol.replace('/', '').replace('USDT', 'USD').upper()
        d1 = {
            "event": "subscribe",
            "channel": "book",
            "pair": __sym,
            "prec": "P0",
            "freq": "F0",
            "length": str(settings.CACHE_ORDER_ROW_LENGTH),
        }
        # d2 = {
        #     "event": "subscribe",
        #     "channel": "trades",
        #     "pair": __sym
        # }
        book_channel_id = None
        # trades_channel_id = None
        ping_rate_limit = rate_limit_generator()
        ping_rate_limit.send(None)
        async with websockets.connect("wss://api.bitfinex.com/ws") as ws:
            await ws.send(json.dumps(d1))
            # await ws.send(json.dumps(d2))
            asks = []
            bids = []

            while True:
                data = json.loads(await asyncio.wait_for(ws.recv(), timeout=30))
                if isinstance(data, dict):
                    if data.get('event') == 'info':
                        self.logger.info(event='get_bitfinex_event', data=data)
                        if data.get('code') == 20051:  # reconn signal
                            return
                        if data.get('code') == 20060:  # pause signal
                            await asyncio.sleep(15)
                            return
                        continue
                    elif data.get('event') == 'error':
                        raise errors.ExchangeError(data)
                    elif data.get('event') == 'subscribed':
                        if data.get('channel') == 'book':
                            book_channel_id = data['chanId']
                        # if data.get('channel') == 'trades':
                        #     trades_channel_id = data['chanId']
                elif isinstance(data, list) and book_channel_id == data[0]:
                    await self._handle_ws_book(data, asks, bids, symbol)
                # elif isinstance(data, list) and trades_channel_id == data[0]:
                #     await self._handle_ws_trades(data)

                if ping_rate_limit.send(('{}.ping'.format(self.name), 5)):
                    await ws.send(json.dumps({"event": "ping"}))

    async def _handle_ws_book(self, data, asks, bids, symbol):
        # pylint: disable=too-many-locals
        recv_time = time.time()
        if len(data) == 2:  # get book snapshot
            if data[1] == 'hb':
                return
            _, ows = data
            asks.clear()
            bids.clear()
            for p, c, a in ows:
                if a >= 0:
                    bids.append(OrderRow(price=p, count=c, amount=a))
                else:
                    asks.append(OrderRow(price=p, count=c, amount=-a))
        elif len(data) == 4:  # get change
            _conn_id, price, count, amount = data
            side_ows = bids if amount >= 0 else asks
            amount = abs(amount)
            ow = OrderRow(price=price, count=count, amount=amount)
            # Binary search [O(logn)]
            ind = bisect_right(
                side_ows, ow, key=lambda o: o.price, rv=side_ows is bids
            )
            l_ind = ind-1
            if l_ind >= 0 and side_ows[l_ind].price == ow.price:
                if count == 0:
                    side_ows.pop(l_ind)
                else:
                    side_ows[l_ind] = ow
            else:
                side_ows.insert(ind, ow)
        ob = OrderBook(exchange=self,
                       symbol=symbol,
                       bids=bids,
                       asks=asks,
                       timestamp=recv_time)
        self.set_book(ob)

    async def _handle_ws_trades(self):
        pass

    async def cancel_all(self):
        pass


if __name__ == '__main__':
    lp = asyncio.get_event_loop()
    bf = Bitfinex('bitfinex', {})
    lp.run_until_complete(bf.set_orderbook_d('BTC/USDT'))

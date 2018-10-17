# !/usr/bin/env python
__author__ = 'Rick Zhang'
__time__ = '2018/10/12'

import asyncio
import time
from typing import List

from arbcharm import settings
from arbcharm.models import BaseExchange, Order, OrderBook, Trade, get_exchange
from arbcharm.tools import get_logger, rate_limit_generator
from ccxt.base import errors as ccxt_errors


class ArbCharm:
    def __init__(self, symbol, exchanges: List[BaseExchange]):
        self.symbol = symbol
        self.exchanges = exchanges
        self.name = 'ArbCharm-{}'.format(self.symbol)
        self.trade_limit = rate_limit_generator()
        self.trade_limit.send(None)
        self.logger = get_logger(self.name)
        self.is_running = False

    async def start(self):
        self.is_running = True
        self.logger.info(event='arbcharm_start')

        for e in self.exchanges:
            asyncio.ensure_future(e.set_orderbook_d(self.symbol))

        alerter_exc = get_exchange('binance', {})
        while self.is_running:
            await alerter_exc.wait_book_update(self.symbol)
            await self.arbitrage()
            alerter_exc.reset_book_update(self.symbol)

        # TODO cancel all orders
        self.logger.info(event='arbcharm_exit')

    def close(self):
        self.is_running = False

    async def arbitrage(self):
        now = time.time()
        ob_l = self.get_valide_ob_l()
        if len(ob_l) < 2:
            return

        self.logger.info(
            event='arbitrage',
            market_price={ob.exchange.name: (ob.asks[0].price+ob.bids[0].price)/2 for ob in ob_l},
            time_delay={ob.exchange.name: now-ob.timestamp for ob in ob_l},
        )
        trades = auto_match(ob_l)
        opportunity = self.find_opportunity_from_trade(trades)

        if opportunity:
            self.logger.info(
                event='found_opportunity',
                opportunity=[o.to_dict() for o in opportunity],
            )
            await self.catch_opportunity(opportunity)
            await asyncio.sleep(3)

    def get_valide_ob_l(self):
        now = time.time()
        ob_l = []
        for e in self.exchanges:
            book = e.get_book(self.symbol)
            if book and now - book.timestamp < 1:
                ob_l.append(book)
        return ob_l

    def find_opportunity_from_trade(self, trades: List[Trade]) -> List[Order]:
        rate = settings.ARBITRAGE_OPPORTUNITY_RATE
        orders = {}

        for t in trades:
            if (t.bid_price-t.ask_price)/t.ask_price > rate:
                od = orders.get(
                    t.ask_exc,
                    Order(
                        exc=t.ask_exc,
                        symbol=self.symbol,
                        price=t.ask_price,
                        amount=0,
                        side=Order.SIDE_BUY,
                    )
                )
                assert od.side == Order.SIDE_BUY
                od.amount += t.amount
                od.price = max(od.price, t.ask_price)
                orders[od.exc] = od

                od = orders.get(
                    t.bid_exc,
                    Order(
                        exc=t.bid_exc,
                        symbol=self.symbol,
                        price=t.bid_price,
                        amount=0,
                        side=Order.SIDE_SELL,
                    )
                )
                assert od.side == Order.SIDE_SELL
                od.amount += t.amount
                od.price = min(od.price, t.bid_price)
                orders[od.exc] = od

        return list(orders.values())

    async def catch_opportunity(self, opportunity: List[Order]):
        order_task = []
        for o in opportunity:
            fixd_am = self.fix_amount(o.amount)
            if o.side == Order.SIDE_BUY:
                order_task.append(
                    self.deal_buy(o.exc, fixd_am, o.price)
                )
            if o.side == Order.SIDE_SELL:
                order_task.append(
                    self.deal_sell(o.exc, fixd_am, o.price)
                )

        await asyncio.wait(order_task)

    def fix_amount(self, amount):
        amount_mul = settings.ARBCHARM_AMOUNT_MULTIPLIER
        config_min_amount = max([e.ccxt_exchange.min_amount for e in self.exchanges])
        return max(amount*amount_mul, config_min_amount)

    async def deal_buy(self, exchange: BaseExchange, amount, price):
        if settings.MODE != 'prd':
            return
        try:
            res = await exchange.ccxt_exchange.create_limit_buy_order(
                self.symbol,
                amount,
                price,
            )
        except ccxt_errors.BaseError:
            self.logger.exception()
            return

        oid = res['id']
        await asyncio.sleep(3)
        await self.deal_cancel(exchange, oid)
        await self.save_order_and_trade(exchange, oid)

    async def deal_sell(self, exchange: BaseExchange, amount, price):
        if settings.MODE != 'prd':
            return
        try:
            res = await exchange.ccxt_exchange.create_limit_sell_order(
                self.symbol,
                amount,
                price,
            )
        except ccxt_errors.BaseError:
            self.logger.exception()
            return

        oid = res['id']
        await asyncio.sleep(3)
        await self.deal_cancel(exchange, oid)
        await self.save_order_and_trade(exchange, oid)

    async def deal_cancel(self, exchange: BaseExchange, oid):
        cancel_success = False
        while not cancel_success:
            try:
                await exchange.ccxt_exchange.cancel_order(oid)
                cancel_success = True
                self.logger.info(event='cancel_order_success', oid=oid, exchange=exchange.name)
            except ccxt_errors.OrderNotFound:
                cancel_success = True
            except ccxt_errors.BaseError as e:
                self.logger.exception(error_class=e.__class__.__name__)
                await asyncio.sleep(3)
        return oid

    async def save_order_and_trade(self, exchange: BaseExchange, oid):
        pass

    def __str__(self):
        return self.name


def auto_match(ob_l: List[OrderBook]) -> List[Trade]:
    """
    orderbook成交函数
    :param ob_l: 多个交易所和当前的orderbook
    :return: 成交列表
    """
    bid_row_l = []
    for ob in ob_l[::-1]:  # 相同条件下, 放在前面的交易所得到优先成交
        bid_row_l.extend([[ob.exchange, ow] for ow in ob.bids])
    bid_row_l = sorted(bid_row_l, key=lambda i: i[1].price)  # best order row at last index

    ask_row_l = []
    for ob in ob_l[::-1]:
        ask_row_l.extend([[ob.exchange, ow] for ow in ob.asks])
    ask_row_l = sorted(ask_row_l, key=lambda i: i[1].price, reverse=True)

    trade_l = []
    bid_retain_row = None
    ask_retain_row = None
    while bid_row_l and ask_row_l:
        bid_exc, bid_ow = bid_retain_row if bid_retain_row else bid_row_l.pop()
        ask_exc, ask_ow = ask_retain_row if ask_retain_row else ask_row_l.pop()
        if bid_ow.price < ask_ow.price:
            break

        if bid_ow.amount < ask_ow.amount:
            amount = bid_ow.amount
            ask_ow.amount = ask_ow.amount - amount
            bid_retain_row, ask_retain_row = None, [ask_exc, ask_ow]
        elif bid_ow.amount == ask_ow.amount:
            amount = bid_ow.amount
            bid_retain_row, ask_retain_row = None, None
        else:
            amount = ask_ow.amount
            bid_ow.amount = bid_ow.amount - amount
            bid_retain_row, ask_retain_row = [bid_exc, bid_ow], None

        trade_l.append(
            Trade(
                bid_exc=bid_exc,
                ask_exc=ask_exc,
                bid_price=bid_ow.price,
                ask_price=ask_ow.price,
                amount=amount,
            )
        )
    return trade_l


if __name__ == "__main__":
    lp = asyncio.get_event_loop()
    ac = ArbCharm('BTC/USDT', [get_exchange(e, {}) for e in ('binance', 'bitfinex', 'huobipro')])
    lp.run_until_complete(ac.start())

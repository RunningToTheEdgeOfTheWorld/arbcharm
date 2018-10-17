# !/usr/bin/env python
__author__ = 'Rick Zhang'
__time__ = '2018/10/12'

import asyncio

print('server start')

main_loop = asyncio.get_event_loop()


def main():
    start_arbtrage_task()


def start_arbtrage_task():
    from arbcharm import settings
    from arbcharm.charm import ArbCharm
    from arbcharm.models import get_exchange

    tasks = []
    for sym, exc_dict in settings.ARB_CONF.items():
        excs = [get_exchange(e, config) for e, config in exc_dict.items()]
        tasks.append(ArbCharm(sym, excs).start())

    cortasks = asyncio.gather(*tasks)
    main_loop.run_until_complete(cortasks)


main()

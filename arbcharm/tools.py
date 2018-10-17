# !/usr/bin/env python
__author__ = 'Rick Zhang'
__time__ = '2018/10/12'

import logging
import sys
import time

from arbcharm.json_logger import JsonFormatter, get_json_logger


def bisect_right(a, x, key=None, lo=0, hi=None, rv=False):  # pylint: disable=too-many-arguments
    """
    binary search
    :param a: a list
    :param x: target value
    :param key: sort_attr
    :param lo: start_index
    :param hi: end_index
    :param rv: reverse
    :return: index of insert
    """
    key = key if key else lambda i: i
    if lo < 0:
        raise ValueError('lo must be non-negative')
    if hi is None:
        hi = len(a)
    while lo < hi:
        mid = (lo+hi)//2
        if rv:
            if key(x) > key(a[mid]):
                hi = mid
            else:
                lo = mid+1
        else:
            if key(x) < key(a[mid]):
                hi = mid
            else:
                lo = mid+1
    return lo


def get_logger(name='root'):
    class LevelFilter(object):
        def __init__(self, level):
            self.__level = level

        def filter(self, log_record):
            return log_record.levelno <= self.__level

    logger = get_json_logger(name)
    logger.propagate = False
    if not logger.handlers:
        formatter = JsonFormatter(
            {
                'logger': name,
                'asctime': '%(asctime)s',
                'level': '%(levelname)s',
                'message': '%(message)s',
            }
        )

        sh_i = logging.StreamHandler(sys.stdout)
        sh_i.setLevel(logging.INFO)
        sh_i.setFormatter(formatter)
        sh_i.addFilter(LevelFilter(logging.INFO))

        sh_e = logging.StreamHandler(sys.stderr)
        sh_e.setFormatter(formatter)
        sh_e.setLevel(logging.ERROR)

        logger.addHandler(sh_i)
        logger.addHandler(sh_e)
    return logger


def rate_limit_generator():
    """
    usage:
        r = rate_limit_generator()
        r.send(None)  # start generator
        r.send(('place_one', 10))  # input key and time interval
    yield True while allow to access
    """
    loc_time_map = {}  # {key: timestamp}
    key, min_time_interval = yield True
    while True:
        early_time = loc_time_map.get(key)
        now = time.time()
        if early_time:
            if (now - early_time) > min_time_interval:
                access = True
                loc_time_map[key] = time.time()
            else:
                access = False
        else:
            loc_time_map[key] = time.time()
            access = True
        key, min_time_interval = yield access


def print_cost_time(func):
    def _func(*args, **kwargs):
        t1 = time.time()
        res = func(*args, **kwargs)
        print(time.time() - t1)
        return res
    return _func()

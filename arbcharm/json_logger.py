# !/usr/bin/env python
__author__ = 'Rick Zhang'
__time__ = '2018/7/10'

# pylint: disable=arguments-differ

import json
import logging
import traceback


class JsonLogger(logging.Logger):
    def __init__(self, *args, **kwargs):
        self.__formater = None
        super().__init__(*args, **kwargs)
        self.propagate = False

    def debug(self, msg=None, **kwargs):
        msg, _args, _kwargs = self._parse_arge(msg, **kwargs)
        return super().debug(msg, *_args, **_kwargs)

    def info(self, msg=None, **kwargs):
        msg, _args, _kwargs = self._parse_arge(msg, **kwargs)
        return super().info(msg, *_args, **_kwargs)

    def warning(self, msg=None, **kwargs):
        msg, _args, _kwargs = self._parse_arge(msg, **kwargs)
        return super().warning(msg, *_args, **_kwargs)

    def error(self, msg=None, **kwargs):
        msg, _args, _kwargs = self._parse_arge(msg, **kwargs)
        return super().error(msg, *_args, **_kwargs)

    def exception(self, msg=None, **kwargs):
        kwargs['traceback'] = traceback.format_exc().splitlines()
        msg, _args, _kwargs = self._parse_arge(msg, **kwargs)
        return super().error(msg, *_args, **_kwargs)

    def critical(self, msg=None, **kwargs):
        msg, _args, _kwargs = self._parse_arge(msg, **kwargs)
        return super().critical(msg, *_args, **_kwargs)

    @staticmethod
    def _parse_arge(msg, **kwargs):
        if 'msg' in kwargs:
            raise ValueError('msg is not allowed in kwargs')
        _args = kwargs.pop('_args', [])
        _kwargs = kwargs.pop('_kwargs', {})
        if msg is not None:
            kwargs['msg'] = msg
        msg = format_msg(kwargs)
        return msg, _args, _kwargs

    def addHandler(self, hdlr):
        if hasattr(self, 'formaater') and not isinstance(hdlr.formatter, JsonFormatter):
            raise ValueError('Please use JsonFormatter!')
        super().addHandler(hdlr)


root = JsonLogger(logging.INFO)
json_manager = logging.Manager(root)
json_manager.loggerClass = JsonLogger

JsonLogger.manager = json_manager
JsonLogger.root = root


def get_json_logger(name=None):
    if name:
        return JsonLogger.manager.getLogger(name)
    return root


def format_msg(msg):
    """
    transfor msg dict jsonable dict
    :param: msg
    :return: json
    """
    def _format_msg(_m):
        if isinstance(_m, (str, int, float)):
            return _m
        elif isinstance(_m, bytes):
            return _m.decode()
        elif isinstance(_m, dict):
            return {_format_msg(k): _format_msg(v) for k, v in _m.items()}
        elif isinstance(_m, (tuple, list)):
            return [_format_msg(i) for i in _m]
        else:
            try:
                return str(_m)
            except:
                raise ValueError("Not allowed object, object must have __str__ method!")

    return json.dumps(_format_msg(msg))


class JsonFormatter(logging.Formatter):
    def __init__(self, fmt_dict: dict = None, datefmt=None, style='%'):
        if not fmt_dict:
            fmt_dict = {
                'asctime': '%(asctime)s',
                'level': '%(levelname)s',
                'message': '%(message)s',
            }
        if not isinstance(fmt_dict, dict):
            raise ValueError('fmt_dict must be a dict')

        fmt = format_msg(fmt_dict).replace('"%(message)s"', '%(message)s')
        super().__init__(fmt, datefmt, style)


_default_formatter = JsonFormatter()
_default_handler = logging.StreamHandler()
_default_handler.setLevel(logging.INFO)
_default_handler.formatter = _default_formatter
root.addHandler(_default_handler)


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    logger = get_json_logger('test')
    logger.addHandler(_default_handler)
    logger.info(word='Hello world')
    try:
        raise RuntimeError()
    except RuntimeError:
        logger.exception('Hello world')

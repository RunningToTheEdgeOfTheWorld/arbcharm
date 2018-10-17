# !/usr/bin/env python
__author__ = 'Rick Zhang'
__time__ = '2018/10/14'

import sys
from codecs import open as openc
from os import path

from setuptools import find_packages, setup

here = path.abspath(path.dirname(__file__))


py_version = sys.version_info
assert py_version.major == 3
assert py_version.minor >= 5

with openc(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

with openc('requirements.txt', 'r') as f:
    require_list = [line.strip() for line in f]

setup(
    name='arbcharm',
    version='1.0.0',
    description='Charm Of Arbitrage',
    long_description=long_description,
    url='https://github.com/RunningToTheEdgeOfTheWorld/arbcharm',
    author='Rick Zhang',
    author_email='rickzhangjie@gmail.com',
    license='MIT',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Build Tools',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
    ],
    keywords='',
    packages=find_packages(),
    install_requires=require_list,
    extras_require={
        'dev': [
        ],
        'test': ['coverage'],
    },
    package_data={
        '': ['*.*'],
    },
)

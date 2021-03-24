# arbcharm （已停止更新，有需求可以联系我）

## 简介
套利的艺术
* 使用python3协程接入主流数字货币交易所websocket, 只需在配置文件./settings.py中配置密钥即可。
* 系统响应时延小于6ms
* 目前支持的主流数字货币交易所包括：
    * bitfinex
    * binance
    * huobipro

## 使用
项目启动需要依赖以下组件：

* docker

启动步骤：

1. 执行./build.sh构建镜像。
2. 执行./start.sh启动服务。

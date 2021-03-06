#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import datetime

import nonebot

# Custom your logger
# 
from nonebot.log import logger, default_format
if not os.path.exists('logs/'):
    os.mkdir('logs')
time_info = datetime.datetime.today().strftime('%Y-%m-%d-%H-%M-%S')
logger.add(f"logs/error-{time_info}.log",
           rotation="00:00",
           diagnose=False,
           level="ERROR",
           format=default_format)

# You can pass some keyword args config to init function
from nonebot.adapters.mirai import WebsocketBot

nonebot.init()
app = nonebot.get_asgi()

nonebot.get_driver().register_adapter('mirai-ws', WebsocketBot, qq=3101482118)

nonebot.load_builtin_plugins()
nonebot.load_plugins("src/plugins")
nonebot.load_plugin("nonebot_plugin_test")
nonebot.load_plugin("nonebot_plugin_apscheduler")


if __name__ == "__main__":
    nonebot.run()

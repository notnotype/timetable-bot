import datetime
import re
from typing import Union

import nonebot
from nonebot.log import logger
from nonebot.typing import T_State
from nonebot import on_command, require
from nonebot.adapters import Event
from apscheduler.triggers.date import DateTrigger  # 一次性触发器
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from nonebot.adapters.mirai import MessageSegment, MessageChain, Bot

__plugin_name__ = '提醒我一下'
__plugin_usage__ = '''【提醒 10s】
可用的参数有
d：天
h：时
m：分
s：秒'''

scheduler: AsyncIOScheduler = require('nonebot_plugin_apscheduler').scheduler

noteme_command = on_command('noteme', aliases={'提醒', '提醒我'})


def parse_time(msg: str) -> Union[datetime.timedelta, None]:
    try:
        _delta = datetime.timedelta(seconds=0)
        if match_result := re.match(r'(\d+)s', msg):
            _delta += datetime.timedelta(seconds=int(match_result.group(1)))
        if match_result := re.match(r'(\d+)m|(\d+)min', msg):
            _delta += datetime.timedelta(minutes=int(match_result.group(1)))
        if match_result := re.match(r'(\d+)h', msg):
            _delta += datetime.timedelta(hours=int(match_result.group(1)))
        if match_result := re.match(r'(\d+)d', msg):
            _delta += datetime.timedelta(days=int(match_result.group(1)))
        if _delta >= datetime.timedelta(seconds=1):
            return _delta
        else:
            return None
    except OverflowError:
        return None


@noteme_command.handle()
async def _(bot: Bot, event: Event, state: T_State):
    stripped_arg = event.get_plaintext().strip()
    if stripped_arg:
        if (delta := parse_time(stripped_arg)) is not None:
            state['delta'] = delta
        else:
            await noteme_command.finish('格式错误')


@noteme_command.got('delta', prompt='需要我多久后提醒您呢？')
async def add_scheduler(bot: Bot, event: Event, state: T_State):
    def async_wrapper(func):
        async def wrapper(*args, **kwargs):
            await func(*args, **kwargs)

        return wrapper

    delta = state['delta']
    # delta = datetime.timedelta(minutes=5)
    await bot.send(event, f' 我将在{str(delta)}后提醒您', at_sender=True)
    trigger = DateTrigger(
        run_date=datetime.datetime.now() + delta
    )
    scheduler.add_job(
        func=async_wrapper(bot.send),  # 要添加任务的函数，不要带参数
        trigger=trigger,  # 触发器
        args=(event, MessageChain('提醒您了！'),),  # 函数的参数列表，注意：只有一个值时，不能省略末尾的逗号
        kwargs={'at_sender': True},
        misfire_grace_time=60,  # 允许的误差时间，建议不要省略
    )


@noteme_command.args_parser
async def _(bot: Bot, event: Event, state: T_State):
    stripped_arg = event.get_plaintext().strip()

    if not stripped_arg:
        await noteme_command.reject('时间不能为空呢，请重新输入')
    if (delta := parse_time(stripped_arg)) is not None:
        state['delta'] = delta
    else:
        await noteme_command.reject('格式错误')

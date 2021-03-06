import datetime
import re
from pathlib import Path
from json import dumps, loads
from typing import Union, List, Tuple, Dict

import nonebot
from apscheduler.triggers.date import DateTrigger
from nonebot import get_driver
from nonebot import require
from nonebot import on_command
from nonebot.rule import to_me
from nonebot.typing import T_State
from nonebot.matcher import Matcher
from nonebot.adapters.mirai import Bot, Event, MessageChain
from nonebot import get_driver
from nonebot.log import logger
from apscheduler.schedulers.base import BaseScheduler, Job

from .functions import (
    f_generate_scheduler,
    f_bind,
    get_current_teaching_week,
    get_teaching_week_date_range,
    index_datetime
)
from .model import StudentTimetable
from .config import Config
from .data_source import Hnust

global_config = get_driver().config
driver = get_driver()
config = Config(**global_config.dict())
schedules_mapping: Dict[str, List[Job]] = {}

_sub_plugins = set()
_sub_plugins |= nonebot.load_plugins(str((Path(__file__).parent / "plugins").resolve()))

scheduler: BaseScheduler = require('nonebot_plugin_apscheduler').scheduler

__plugin_name__ = 'hnust课表提醒机器人'
__plugin_usage__ = '先输入“绑定”来绑定课表哦'

bind_command = on_command('bind', aliases={'绑定'})
register_scheduler_command = on_command('注册我的计划任务', aliases={'计划任务', '注册'})
next_command = on_command('next')


@bind_command.handle()
async def _(bot: Bot, event: Event, state: T_State):
    stripped_arg = event.get_plaintext().strip()
    if stripped_arg:
        r = re.match('\s*(\d+)\s+(.+)\s*', stripped_arg)
        if r:
            state['student_id'] = r.group(1)
            state['password'] = r.group(2)
    return


@bind_command.got('student_id', prompt='请 input 您的 student_id')
@bind_command.got('password', prompt='请 input 您的 password')
async def bind(bot: Bot, event: Event, state: T_State, matcher: Matcher):
    qq_id = int(event.get_user_id())
    student_id = state['student_id']
    password = state['password']


    r = await f_bind(qq_id, student_id, password)
    if r[0]:
        await matcher.send('绑定成功!')
    else:
        await matcher.send(f'绑定失败: {r[1]}')


    # await matcher.send(f'{qq_id}, {student_id}, {password}')


@bind_command.args_parser
async def _(bot: Bot, event: Event, state: T_State):
    stripped_arg = event.get_plaintext().strip()
    if not stripped_arg:
        await bind_command.reject('输入不能为空呢，请重新输入')
    if state["_current_key"] == 'student_id':
        try:
            state['student_id'] = int(stripped_arg)
        except ValueError:
            await bind_command.reject('您输入的不是数字呢！请重新输入')
    elif state["_current_key"] == 'password':
        try:
            state['password'] = stripped_arg
        except ValueError:
            await bind_command.reject('您输入的不是数字呢！请重新输入')
    else:
        raise RuntimeError(f'at: bind_command.args_parser # {state["_current_key"]}')


@register_scheduler_command.handle()
async def register_scheduler(bot: Bot, event: Event, state: T_State, matcher: Matcher):
    # logger.opt(colors=True).debug(str(list(event.get_message())))
    uid = event.get_user_id()
    striped_message = event.get_plaintext()
    if striped_message:
        try:
            teaching_week = int(striped_message) - 1
        except ValueError:
            await register_scheduler_command.finish('请输入数字')
            return
    else:
        teaching_week = get_current_teaching_week()

    student = StudentTimetable.select().where(StudentTimetable.qq_id == event.get_user_id())

    if not student:
        await matcher.finish('您还没有绑定哟！输入”绑定“跟随指引绑定')
    else:
        student = student[0]

    student_id = student.student_id
    password = student.password

    if not student.band:
        await matcher.finish('您还没有绑定哟！输入”绑定“跟随指引绑定')

    user_all_timetables = student.timetables
    if not user_all_timetables:
        try:

            await register_scheduler_command.send('请稍等, 正在下载课表...')

            hnust = Hnust()
            await hnust.login(student_id, password)
            user_all_timetables = await hnust.get_all_timetable()
            await hnust.close()

            student.timetables = dumps(user_all_timetables)
            student.band = True
            student.save()

        except RuntimeError as e:
            await register_scheduler_command.pause(str(e.args[0]))
            return
    else:
        user_all_timetables = loads(user_all_timetables)

    user_schedules = f_generate_scheduler(timetable=user_all_timetables[str(teaching_week + 1)])
    user_schedules = list(filter(lambda o: o[0] > datetime.datetime.today(), user_schedules))

    # first remove/cancel old jobs, then add new jobs
    if uid in schedules_mapping:
        for each in schedules_mapping[uid]:
            each.remove()
    schedules_mapping[uid] = []

    for each in user_schedules:
        trigger = DateTrigger(
            each[0]
        )
        job = scheduler.add_job(
            func=matcher.send,
            trigger=trigger,
            args=(each[1],),
            misfire_grace_time=60,
        )
        schedules_mapping[uid].append(job)
        print(f'添加任务成功\n将在：{each[0]}触发\n触发信息：{each[1]}\n')

    a, b = get_teaching_week_date_range(teaching_week)
    time_format = '%Y-%m-%d'
    a_format = a.strftime(time_format)
    b_format = b.strftime(time_format)
    teaching_week_msg = f'第{teaching_week + 1}教学周（{a_format} - {b_format}）'
    if not user_schedules:
        await matcher.send(f'{teaching_week_msg}\n没有课添加哦!')
    else:
        await matcher.send(f'{teaching_week_msg}\n课程任务成功!共添加了{len(user_schedules)}个提醒任务')


# todo debug
@next_command.handle()
async def _(bot: Bot, event: Event, state: T_State):
    student = StudentTimetable.select().where(StudentTimetable.qq_id == event.get_user_id())

    if not student:
        await next_command.finish('您还没有绑定哟！输入”绑定“跟随指引绑定')
    else:
        student = student[0]

    student_id = student.student_id
    password = student.password

    if not all([student_id, password]):
        await next_command.finish('您还没有绑定哟！输入”绑定“跟随指引绑定')

    user_all_timetables = student.timetables
    if not user_all_timetables:
        try:

            await next_command.send('请稍等, 正在下载课表...')

            hnust = Hnust()
            await hnust.login(student_id, password)
            user_all_timetables = await hnust.get_all_timetable()
            await hnust.close()

            student.timetables = dumps(user_all_timetables)
            student.save()

        except RuntimeError as e:
            await next_command.pause(str(e.args[0]))
            return
    else:
        user_all_timetables = loads(user_all_timetables)

    timetable = user_all_timetables[str(get_current_teaching_week() + 1)]
    # timetable = user_all_timetables[str(2)]

    now = datetime.datetime.today()

    def filter_timetable(o):
        _index = int(o['classTime'][1])
        _start_day = datetime.datetime.strptime(o['date'], '%Y-%m-%d')
        _start_time, _end_time = index_datetime(_start_day, _index)
        return datetime.datetime(year=now.year, month=now.month, day=now.day + 1) > _start_time > now

    later_timetable = list(filter(filter_timetable, timetable))
    if later_timetable:
        index = int(later_timetable[0]['classTime'][1])
        start_day = datetime.datetime.strptime(later_timetable[0]['date'], '%Y-%m-%d')
        start_time, end_time = index_datetime(start_day, index)
        await next_command.send(f'{start_time}')
    else:
        await next_command.send('今天没有课啦!')


async def register_all_timetable(bot):
    """注册所有用户的计划任务"""
    students = StudentTimetable.select()

    # bot: Bot = list(nonebot.get_bots().values())[0]
    # await bot.send_friend_message(1, MessageChain('1'))
    def async_wrapper(func):
        async def wrapper(*args, **kwargs):
            await func(*args, **kwargs)
        return wrapper()

    for student in students:
        timetables = student.timetables
        if timetables:
            uid = qq_id = student.qq_id
            student_id = student.student_id

            user_all_timetables = loads(timetables)
            teaching_week = get_current_teaching_week()

            user_schedules = f_generate_scheduler(timetable=user_all_timetables[str(teaching_week + 1)])
            user_schedules = list(filter(lambda o: o[0] > datetime.datetime.today(), user_schedules))

            # first remove/cancel old jobs, then add new jobs
            if uid in schedules_mapping:
                for each in schedules_mapping[uid]:
                    each.remove()
            schedules_mapping[uid] = []

            for each in user_schedules:
                trigger = DateTrigger(
                    each[0]
                )
                job = scheduler.add_job(
                    func=bot.send_friend_message,
                    trigger=trigger,
                    args=(uid, MessageChain(each[1]),),
                    misfire_grace_time=60,
                )
                schedules_mapping[uid].append(job)
                print(f'添加任务成功\n将在：{each[0]}触发\n触发信息：{each[1]}\n')

            a, b = get_teaching_week_date_range(teaching_week)
            time_format = '%Y-%m-%d'
            a_format = a.strftime(time_format)
            b_format = b.strftime(time_format)

            await bot.send_friend_message(uid, MessageChain('自动任务启动， 开始注册今日课程'))
            teaching_week_msg = f'第{teaching_week + 1}教学周（{a_format} - {b_format}）'
            if not user_schedules:
                await bot.send_friend_message(uid, MessageChain(f'{teaching_week_msg}\n没有课添加哦!'))
            else:
                await bot.send_friend_message(
                    uid, MessageChain(f'{teaching_week_msg}\n课程任务成功!共添加了{len(user_schedules)}个提醒任务')
                )


@driver.on_bot_connect
async def register_schedule_startup(bot):
    await register_all_timetable(bot)


@scheduler.scheduled_job(
    'cron',
    # year=None,
    # month=None,
    # day=None,
    # week=None,
    # day_of_week="mon,tue,wed,thu,fri",
    hour=3,  # 每天凌晨3点
    # minute=None,
    # second=1,
    # start_date=None,
    # end_date=None,
    # timezone=None,
)
async def register_timetable_everyday():
    bot = list(nonebot.get_bots().values())[0]
    await register_all_timetable(bot)

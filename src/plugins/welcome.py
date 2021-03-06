import nonebot

from nonebot import on_request, on_notice, on_command
from nonebot import Bot
from nonebot.typing import T_State
from nonebot.adapters import Event
from nonebot.matcher import Matcher

from nonebot.adapters.mirai import NewFriendRequestEvent

__plugin_name__ = '发送加好友欢迎信息'
__plugin_usage__ = '添加我为好友'


def NewFriendRequestEventRule(bot: Bot, event: Event, state: T_State):
    return isinstance(event, NewFriendRequestEvent)


new_friend = on_request(NewFriendRequestEventRule)
new_friend_notice = on_notice(NewFriendRequestEventRule)


@new_friend.handle()
async def _(bot: Bot, event: NewFriendRequestEvent, state: T_State):
    await event.approve(bot)


@new_friend_notice.handle()
async def welcome(bot: Bot, event: NewFriendRequestEvent, state: T_State, matcher: Matcher):
    await matcher.send('欢迎欢迎,目前本程序处于测试阶段可能会不稳定QAQ\n'
                       '输入usage来查看帮助哦\n'
                       '目前使用需要教务网密码获取课表（以后可能不要）\n'
                       '输入“绑定”来绑定\n'
                       '输入“计划任务”来注册计划任务\n'
                       '输入“提醒 10s”即可让我在10秒后提醒您哦\n')

import nonebot
from nonebot.rule import to_me
from nonebot.typing import T_State
from nonebot import on_command
from nonebot.adapters import Event
from nonebot.adapters.mirai import Bot
from nonebot.log import logger

usage_command = on_command('usage', aliases={'使用帮助', '帮助', '使用方法', '?'}, rule=to_me())


@usage_command.handle()
async def _(bot: Bot, event: Event, state: T_State):
    # 获取设置了名称的插件列表
    plugins = list(filter(lambda p: p.name, nonebot.get_loaded_plugins()))
    plugin_infos = list(zip(
        [getattr(p, '__plugin_name__', None) or p.name for p in plugins],
        [getattr(p, '__plugin_usage__', '没有描述') for p in plugins]
    ))
    arg = event.get_plaintext().strip()
    if not arg:
        # 如果用户没有发送参数，则发送功能列表
        await usage_command.send(
            '我现在支持的功能有：\n\n' + '\n'.join([p[0] for p in plugin_infos])
        )
        return

    # 如果发了参数则发送相应命令的使用帮助
    if arg:
        for name, info in plugin_infos:
            if name == arg:
                await usage_command.send(info)
    else:
        await usage_command.send('没有此功能')

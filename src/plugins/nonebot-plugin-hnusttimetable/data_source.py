import time
import datetime
from typing import Any, Union, Dict, List
from urllib.parse import urljoin

import nonebot
import aiohttp
from .config import Config

global_config = nonebot.get_driver().config
config = Config(**global_config.dict())

HNUST_BASE_URL = config.HNUST_BASE_URL


class Hnust:
    session: aiohttp.ClientSession
    user_info: dict
    token: str
    timetable_id: str

    def __init__(self):
        self.session = aiohttp.ClientSession(headers={
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                          '(KHTML, like Gecko) Chrome/88.0.4324.182 Safari/537.36 Edg/88.'
                          '0.705.81'
        })

    async def login(self, student_id: int, pwd: str):
        url = urljoin(HNUST_BASE_URL, 'login')
        data = {
            'userNo': student_id,
            'pwd': pwd
        }
        r = await self.session.post(url, data=data)
        resp_json = await r.json()
        if resp_json['code'] == '1':
            self.user_info = resp_json['data']
            self.token = self.user_info['token']
            self.session._default_headers['token'] = self.token
            return resp_json['Msg']
        elif resp_json['code'] == '0':
            self.token = pwd
            url = urljoin(HNUST_BASE_URL, 'Get_sjkbms')
            r = await self.session.post(url)
            resp_json = await r.json()
            if resp_json['code'] == '1':
                return resp_json['Msg']
            else:
                raise RuntimeError(f'登录失败 # {resp_json}')
        else:
            raise RuntimeError(f'登录失败 # {resp_json}')

    async def get_timetable_id(self):
        url = urljoin(HNUST_BASE_URL, 'Get_sjkbms')
        r = await self.session.post(url)
        resp_json = await r.json()
        if resp_json['code'] == 1:
            self.timetable_id = resp_json['data'][0]['kbjcmsid']
            return self.timetable_id
        else:
            raise RuntimeError(f'状态码错误 # {resp_json}')

    async def get_timetable(self, week_num: int = 1) -> list:
        url = urljoin(HNUST_BASE_URL, 'student/curriculum')
        kbjcmsid = await self.get_timetable_id()
        data = {
            'kbjcmsid': kbjcmsid,
            'week': str(week_num),
        }
        r = await self.session.post(url, data=data)
        resp_json = await r.json()
        if resp_json['code'] == '1':
            item_data = resp_json['data'][0]['item']
            date_data = resp_json['data'][0]['date']
            date_mapping = {}
            for each in date_data:
                date_mapping[int(each['xqid']) - 1] = each['mxrq']
            timetable = []
            for each in item_data:
                class_week_details = each['classWeekDetails'].strip(',')
                class_time = each['classTime']
                weekday = int(class_time[0]) - 1
                index = int(class_time[3:5]) // 2
                class_time = str(weekday) + str(index)
                timetable.append({
                    "courseName": each['courseName'],
                    "teacherName": each['teacherName'],
                    "location": each['location'],
                    "classWeekDetails": class_week_details,
                    "classTime": class_time,
                    "date": date_mapping[weekday]
                })
            return timetable
        else:
            raise RuntimeError(f'获取课表id失败 # {resp_json}')

    async def get_all_timetable(self) -> Dict[str, List[Dict]]:
        all_timetable = {}
        teaching_weeks = await self.get_teaching_weeks()
        for teaching_week in teaching_weeks:
            timetable = await self.get_timetable(teaching_week)
            all_timetable[str(teaching_week)] = timetable
        return all_timetable

    async def get_teaching_weeks(self):
        url = urljoin(HNUST_BASE_URL, 'teachingWeek')
        r = await self.session.post(url)
        resp_json = await r.json()
        if resp_json['code'] == '1':
            teaching_weeks = []
            for each in resp_json['data']:
                teaching_weeks.append(int(each['week']))
            return teaching_weeks
        else:
            raise RuntimeError(f'获取教学周失败 # {resp_json}')

    async def close(self):
        await self.session.close()

    async def teaching_day2date(self, teaching_week: int, week_day: int,
                                first_week: Union[str, datetime.date] = None):
        """Monday == 0 ... Sunday == 6."""
        if isinstance(first_week, str):
            first_week = datetime.datetime.strptime('%Y-%m-%d', first_week)
        if first_week is None:
            url = urljoin(HNUST_BASE_URL, 'student/curriculum')
            kbjcmsid = await self.get_timetable_id()
            data = {
                'kbjcmsid': kbjcmsid,
                'week': 1,
            }
            r = await self.session.post(url, data=data)
            resp_json = await r.json()
            if resp_json['code'] == '1':
                first_week = datetime.datetime.strptime(
                    '%Y-%m-%d', resp_json['data'][0]['date'][0]['mxrq']
                )
            else:
                raise RuntimeError(f'状态码错误 # {resp_json}')
        week_delta = datetime.timedelta(days=7)
        day_delta = datetime.timedelta(days=1)
        return first_week + (teaching_week - 1) * week_delta + week_day * day_delta


import asyncio


async def main():
    h = Hnust()
    await h.login(2005010705, 'lyf200211150079.')
    r = await h.get_timetable(2)
    print(r)
    await h.close()


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())

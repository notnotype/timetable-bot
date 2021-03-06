from typing import List, Tuple, Union, Dict
from datetime import datetime, timedelta

from .data_source import Hnust
from .model import StudentTimetable

day = timedelta(days=1)
m40 = timedelta(minutes=40)
m45 = timedelta(minutes=45)
m10 = timedelta(minutes=10)
m5 = timedelta(minutes=5)


def index_datetime_custom(today: datetime, index: int) -> Tuple:
    start_time = None
    end_time = None

    return start_time, end_time


def index_datetime(today: datetime, index: int) -> Tuple[datetime, datetime]:
    start_time = None
    end_time = None

    if index == 1:
        start_time = today + timedelta(hours=8)
        end_time = today + timedelta(hours=9, minutes=40)
    elif index == 2:
        start_time = today + timedelta(hours=10)
        end_time = today + timedelta(hours=11, minutes=40)
    elif index == 3:
        start_time = today + timedelta(hours=14)
        end_time = today + timedelta(hours=15, minutes=40)
    elif index == 4:
        start_time = today + timedelta(hours=16)
        end_time = today + timedelta(hours=17, minutes=40)
    elif index == 5:
        start_time = today + timedelta(hours=19)
        end_time = today + timedelta(hours=20, minutes=40)
    else:
        start_time, end_time = index_datetime_custom(today, index)
    return start_time, end_time


def f_generate_scheduler(timetable: List[Dict]) -> List[Tuple[datetime, str]]:
    schedulers = []
    for each in timetable:
        index = int(each['classTime'][1])
        start_day = datetime.strptime(each['date'], '%Y-%m-%d')

        start_time, end_time = index_datetime(start_day, index)

        note_datetime = start_time - m10
        note_message = render_timetable_msg(
            '{time}在{location}上{course_name}还有{remain_time}就要上课了， 赶紧去上课吧！',
            each, remain_time='10分钟'
        )
        schedulers.append((note_datetime, note_message))

        note_datetime2 = start_time - m10 - m10 - m10
        note_message2 = '''{time}在{location}上{course_name}还有{remain_time}就要上课了， 赶紧去上课吧！'''.format(
            time=str(start_time), location=each['location'],
            course_name=each['courseName'],
            remain_time='30分钟',
        )
        schedulers.append((note_datetime2, note_message2))

        note_datetime3 = start_time - m5
        note_message3 = '''{time}在{location}上{course_name}还有{remain_time}就要上课了， 赶紧取上课吧！'''.format(
            time=str(start_time), location=each['location'],
            course_name=each['courseName'],
            remain_time='5分钟',
        )
        schedulers.append((note_datetime3, note_message3))

        note_datetime4 = end_time
        note_message4 = '''下课了， 休息一下吧！（这句话是不是会显得很烦啊？）'''.format(
            time=str(start_time), location=each['location'],
            course_name=each['courseName'],
            remain_time='5分钟',
        )
        schedulers.append((note_datetime4, note_message4))

    return schedulers


async def f_bind(qq_id: int, student_id: int, password: str) -> Tuple:
    hnust = Hnust()
    try:
        msg = await hnust.login(student_id, password)
        await hnust.close()
        student = StudentTimetable.select().where(StudentTimetable.qq_id == qq_id)
        if not student:
            student = StudentTimetable()
        else:
            student = student[0]
        student.qq_id = qq_id
        student.student_id = student_id
        student.password = password
        student.band = True
        student.save()
        return True, msg
    except RuntimeError as e:
        await hnust.close()
        return False, str(e.args[0])


def get_current_teaching_week() -> int:
    today = datetime.today()
    first_monday = datetime(2021, 3, 1)

    teaching_week = (today - first_monday) // timedelta(days=7)
    return teaching_week


def get_teaching_week_date_range(teaching_week: int) -> Tuple[datetime, datetime]:
    week = timedelta(days=7)
    first_monday = datetime(2021, 3, 1)
    a = first_monday + week * teaching_week
    b = first_monday + week * (teaching_week + 1)
    return a, b


def render_timetable_msg(patter: str, today_timetable: Dict, remain_time, **kwargs) -> str:
    index = int(today_timetable['classTime'][1])
    start_day = datetime.strptime(today_timetable['date'], '%Y-%m-%d')
    start_time, end_time = index_datetime(start_day, index)

    _keyword = ['now', 'time', 'start_time', 'location', 'course_name', 'remain_time']

    clear_kwargs = {}
    for k, v in kwargs.items():
        if k not in _keyword:
            clear_kwargs[k] = v

    msg = patter.format(
        now=getattr(kwargs, 'now', None) or datetime.today(),
        time=getattr(kwargs, 'time', None) or str(start_time),
        start_time=getattr(kwargs, 'start_time', None) or str(start_time),
        location=getattr(kwargs, 'location', None) or today_timetable['location'],
        course_name=getattr(kwargs, 'course_name', None) or today_timetable['courseName'],
        remain_time=remain_time,
        **clear_kwargs
    )
    return msg

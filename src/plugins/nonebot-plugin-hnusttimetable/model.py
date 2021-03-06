import nonebot
from peewee import *

from .config import Config

global_config = nonebot.get_driver().config
config = Config(**global_config.dict())

db = SqliteDatabase(config.SQLITE_DATABASE)


class StudentTimetable(Model):
    band = BooleanField(null=True)
    qq_id = IntegerField()
    student_id = IntegerField()
    password = CharField()
    user_info = TextField(null=True)
    timetables = TextField(null=True)

    class Meta:
        database = db
        table_name = 'student_time_table'


if not db.is_connection_usable():
    db.connect()
if not db.table_exists(StudentTimetable):
    db.create_tables([StudentTimetable])


# temp = [
#     {
#         "courseName": "操作系统",
#         "teacherName": "朱彬",
#         "location": "第五教学楼405",
#         "classWeekDetails": "1,2,3,4,5,6,7,8,9,10,11,12,13,14",
#         "classTime": "10102",
#     },
#     {
#         "courseName": "操作系统",
#         "teacherName": "朱彬",
#         "location": "第五教学楼405",
#         "classWeekDetails": "1,2,3,4,5,6,7,8,9,10,11,12,13,14",
#         "classTime": "10102",
#     },
# ]

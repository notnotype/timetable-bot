from pydantic import BaseSettings


class Config(BaseSettings):
    # Your Config Here
    SQLITE_DATABASE: str = 'db.sqlite'
    HNUST_BASE_URL: str = 'http://kdfw.hnust.edu.cn/bbxyhd/'

    class Config:
        extra = "ignore"

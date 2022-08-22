from functools import cache

from pydantic import BaseSettings


class Settings(BaseSettings):
    DEBUG: bool = False
    DBPATH: str = ""


settings = Settings()

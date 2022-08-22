import dbm
from datetime import datetime
from pathlib import Path
from typing import KeysView
import structlog
from fastapi import FastAPI, Query
from starlette.staticfiles import StaticFiles

from stackcollector.settings import settings
from fastapi.responses import HTMLResponse

HERE = Path(__file__).parent
app = FastAPI()
app.mount("/static", StaticFiles(directory="stackcollector/static"), name="static")

settings.DEBUG = True
logger = structlog.get_logger()


class Node(object):
    def __init__(self, name):
        self.name = name
        self.value = 0
        self.children = {}

    def serialize(self, threshold=None):
        res = {"name": self.name, "value": self.value}
        if self.children:
            serialized_children = [
                child.serialize(threshold)
                for _, child in sorted(self.children.items())
                if child.value > threshold
            ]
            if serialized_children:
                res["children"] = serialized_children
        return res

    def add(self, frames, value):
        self.value += value
        if not frames:
            return
        head = frames[0]
        child = self.children.get(head)
        if child is None:
            child = Node(name=head)
            self.children[head] = child
        child.add(frames[1:], value)

    def add_raw(self, line):
        frames, value = line.split()
        frames = frames.split(";")
        try:
            value = int(value)
        except ValueError:
            return
        self.add(frames, value)


@app.get("/data")
def data(
    from_: datetime = Query(default=None, alias="from"),
    until: datetime = Query(default=None, alias="until"),
    threshold: float = 0,
):
    logger.info("Logging /data", from_=from_, until=until, threshold=threshold)
    root = Node("root")
    logger.info("Opening DB", db=settings.DBPATH)
    with dbm.open(file=settings.DBPATH, flag="c") as db:
        keys: KeysView[dbm._KeyType] = db.keys()
        for k in keys:
            entries: list[bytes] = db[k].split()
            logger.info("entries", entries=entries)
            value: int = 0
            for e in entries:
                host, port, ts, v = e.split(b":")
                ts = int(ts)
                v = int(v)
                if (from_ is None or ts >= from_) and (until is None or ts <= until):
                    value += v
            frames = k.split(";")
            root.add(frames, value)
    return root.serialize(threshold * root.value)


@app.get("/")
def render():
    HERE = Path(__file__).parent
    with open(HERE / "static" / "index.html") as fp:
        return HTMLResponse(content=fp.read(), status_code=200)

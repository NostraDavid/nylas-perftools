import dbm
from datetime import datetime
from pathlib import Path
from typing import Any, KeysView
from structlog import get_logger
from structlog.types import FilteringBoundLogger
from fastapi import FastAPI, Query
from starlette.staticfiles import StaticFiles

from stackcollector.settings import settings
from fastapi.responses import HTMLResponse

HERE: Path = Path(__file__).parent
app: FastAPI = FastAPI()
app.mount("/static", StaticFiles(directory="stackcollector/static"), name="static")

settings.DEBUG = True
logger: FilteringBoundLogger = get_logger()


class Node(object):
    def __init__(self, name) -> None:
        self.name = name
        self.value: int = 0
        self.children: dict = {}

    def serialize(self, threshold: float = None) -> dict[str, Any]:
        result: dict[str, Any] = {"name": self.name, "value": self.value}
        if self.children:
            serialized_children: list = [
                child.serialize(threshold)
                for _, child in sorted(self.children.items())
                if child.value > threshold
            ]
            if serialized_children:
                result["children"] = serialized_children
        return result

    def add(self, frames, value) -> None:
        self.value += value
        if not frames:
            return
        head = frames[0]
        child = self.children.get(head)
        if child is None:
            child = Node(name=head)
            self.children[head] = child
        child.add(frames[1:], value)

    def add_raw(self, line) -> None:
        frames, value = line.split(" ")
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
) -> dict[str, Any]:
    logger.info("Logging /data", from_=from_, until=until, threshold=threshold)
    root = Node("root")
    logger.info("Opening DB", db=settings.DBPATH)
    # note that dbm returns bytes, instead of str
    with dbm.open(settings.DBPATH, "c") as db:
        keys: list[bytes] = db.keys()
        for k in keys:
            entries: list[bytes] = db[k].split(b" ")
            # breakpoint()
            logger.info("entries", entries=entries)
            value: int = 0
            for e in entries:
                if len(e.split(b":")) < 4:
                    continue
                host, port, ts, v = e.split(b":")
                ts = int(ts)
                v = int(v)
                if (from_ is None or ts >= from_) and (until is None or ts <= until):
                    value += v
            frames = k.split(b";")
            root.add(frames, value)
    return root.serialize(threshold * root.value)


@app.get("/")
def render() -> HTMLResponse:
    HERE: Path = Path(__file__).parent
    with open(HERE / "static" / "index.html") as fp:
        return HTMLResponse(content=fp.read(), status_code=200)

import dbm
import time
from contextlib import contextmanager

from requests import ConnectionError, HTTPError, get
from structlog import get_logger
from structlog.types import FilteringBoundLogger

logger: FilteringBoundLogger = get_logger()


@contextmanager
def getdb(dbpath):
    while True:
        try:
            handle = dbm.open(dbpath, "c")
            break
        except dbm.error as exc:
            if exc.args[0] == 11:
                continue
            else:
                raise
    try:
        yield handle
    finally:
        handle.close()


def collect(dbpath: str, host: str, port: int) -> None:
    try:
        resp: Response = get(f"http://{host}:{port}/?reset=true")
        resp.raise_for_status()
    except (ConnectionError, HTTPError) as exc:
        logger.warning("Error collecting data", error=exc, host=host, port=port)
        return
    data = resp.content.splitlines()
    try:
        save(data, host, port, dbpath)
    except Exception as exc:
        logger.warning("Error saving data", error=exc, host=host, port=port)
        return
    logger.info("Data collected", host=host, port=port, num_stacks=len(data) - 2)


def save(data, host, port, dbpath):
    now = int(time.time())
    with getdb(dbpath) as db:
        for line in data[2:]:
            try:
                stack, value = line.split()
            except ValueError:
                continue

            entry = f"{host}:{port}:{now}:{value} "
            if stack in db:
                db[stack] += entry
            else:
                db[stack] = entry

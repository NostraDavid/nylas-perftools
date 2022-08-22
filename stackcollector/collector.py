import dbm
import time

from requests import ConnectionError, HTTPError, get, Response
from structlog import get_logger
from structlog.types import FilteringBoundLogger

logger: FilteringBoundLogger = get_logger()


def collect(dbpath: str, host: str, port: int) -> None:
    try:
        resp: Response = get(f"http://{host}:{port}/?reset=true")
        resp.raise_for_status()
    except (ConnectionError, HTTPError) as exc:
        logger.exception("error collecting data", host=host, port=port)
        return
    data: list[str] = resp.text.splitlines()
    try:
        save(data, host, port, dbpath)
    except Exception as exc:
        logger.warning("error saving data", error=exc, host=host, port=port)
        return
    logger.info("data collected", host=host, port=port, num_stacks=len(data) - 2)


def save(data: list[str], host, port, dbpath) -> None:
    """Save the data to a database"""
    now: int = int(time.time())
    # note that dbm converts strings to bytes; same for keys and values
    with dbm.open(dbpath, "c") as db:
        for line in data[2:]:
            try:
                stack, value = line.split(" ")
            except ValueError:
                continue

            entry = f"{host}:{port}:{now}:{value} "
            if stack in db:
                db[stack] += entry
            else:
                db[stack] = entry

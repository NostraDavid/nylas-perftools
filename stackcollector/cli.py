from time import sleep

import click
import structlog
import uvicorn

from stackcollector.collector import collect
from stackcollector.settings import settings
from stackcollector.visualizer import app

logger = structlog.get_logger()


@click.group()
def sc():
    """StackCollector"""
    pass


@sc.command()
@click.option("--dbpath", "-d", default="/var/lib/stackcollector/db")
@click.option("--host", "-h", multiple=True, default=("localhost",))
@click.option(
    "--ports",
    "-p",
    default="16384",
    help="range: n..m, comma separated: a,b,c, single value: x",
)
@click.option("--interval", "-i", type=int, default=60)
def collector(dbpath: str, host: list[str], ports: list[int], interval: int):
    logger.info("info", dbpath=dbpath, host=host, ports=ports, interval=interval)
    # TODO(emfree) document port format; handle parsing errors
    if ".." in ports:
        start, end = list(map(int, ports.split("..")))
        ports = range(start, end + 1)
    elif "," in ports:
        ports = [int(p) for p in ports.split(",")]
    else:
        ports = [int(ports)]
    while True:
        for h in host:
            for port in ports:
                collect(dbpath, h, port)
        sleep(interval)


@sc.command()
@click.option("--port", type=int, default=5555)
@click.option("--dbpath", "-d", default="/var/lib/stackcollector/db")
def visualizer(port: int, dbpath: str):
    settings.DBPATH = dbpath
    uvicorn.run(app, host="0.0.0.0", port=port)

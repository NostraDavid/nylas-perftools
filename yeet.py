from time import sleep
import asyncio

from stacksampler import run_profiler
from yote import a

run_profiler()


for x in range(100):
    print(f"step {x}")
    x += 1
    a()

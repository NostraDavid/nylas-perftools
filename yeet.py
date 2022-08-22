from time import sleep
import asyncio

from stacksampler import run_profiler

run_profiler()

x = 0
while True:
    print(f"step {x}")
    x += 1
    sleep(1)

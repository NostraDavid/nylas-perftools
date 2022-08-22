from time import sleep
import asyncio

import stacksampler

asyncio.run(stacksampler.run_profiler())

x = 0
while True:
    print(f"step {x}")
    x += 1
    sleep(1)

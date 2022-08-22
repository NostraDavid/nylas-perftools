"""
Statistical profiling for long-running Python processes. This was built to work
with gevent, but would probably work if you ran the emitter in a separate OS
thread too.

Example usage
-------------
Add
>>> gevent.spawn(run_profiler, '0.0.0.0', 16384)

in your program to start the profiler, and run the emitter in a new greenlet.
Then curl localhost:16384 to get a list of stack frames and call counts.
"""

from __future__ import print_function

import atexit
from collections import defaultdict
import signal
from types import FrameType
import time
from typing import Iterable
from structlog import get_logger
from structlog.types import FilteringBoundLogger
from werkzeug.serving import BaseWSGIServer, WSGIRequestHandler
from werkzeug.wrappers import Request, Response
from threading import Thread

logger: FilteringBoundLogger = get_logger()


class Sampler(object):
    """
    A simple stack sampler for low-overhead CPU profiling: samples the call
    stack every `interval` seconds and keeps track of counts by frame. Because
    this uses signals, it only works on the main thread.
    """

    def __init__(self, interval=0.005) -> None:
        self.interval: float = interval
        self._started = None
        self._stack_counts: defaultdict[str, int] = defaultdict(int)

    def start(self) -> None:
        self._started: float = time.time()
        try:
            signal.signal(signal.SIGVTALRM, self._sample)
        except ValueError:
            raise ValueError("Can only sample on the main thread")

        signal.setitimer(signal.ITIMER_VIRTUAL, self.interval)
        atexit.register(self.stop)

    def _sample(self, signum: int, frame: FrameType | None) -> None:
        stack: list = []
        while frame is not None:
            stack.append(self._format_frame(frame))
            frame: FrameType | None = frame.f_back

        stack_scsv: str = ";".join(reversed(stack))
        self._stack_counts[stack_scsv] += 1
        signal.setitimer(signal.ITIMER_VIRTUAL, self.interval)

    def _format_frame(self, frame: FrameType) -> str:
        return f"{frame.f_code.co_name}({frame.f_globals.get('__name__')})"

    def output_stats(self) -> str:
        if self._started is None:
            return ""
        elapsed: float = time.time() - self._started
        lines: list[str] = [
            f"elapsed {elapsed}",
            f"granularity {self.interval}",
        ]
        ordered_stacks: list[tuple[str, int]] = sorted(
            self._stack_counts.items(), key=lambda kv: kv[1], reverse=True
        )
        lines.extend([f"{frame} {count}" for frame, count in ordered_stacks])
        return "\n".join(lines) + "\n"

    def reset(self) -> None:
        self._started = time.time()
        self._stack_counts = defaultdict(int)

    def stop(self) -> None:
        self.reset()
        signal.setitimer(signal.ITIMER_VIRTUAL, 0)

    def __del__(self) -> None:
        self.stop()


class Emitter(Thread):
    """A really basic HTTP server that listens on (host, port) and serves the
    process' profile data when requested. Resets internal sampling stats if
    reset=true is passed."""

    def __init__(self, sampler: Sampler, host: str, port: int) -> None:
        self.sampler: Sampler = sampler
        self.host: str = host
        self.port: int = port
        Thread.__init__(self)

    def handle_request(self, environ, start_response) -> Iterable[bytes]:
        stats = self.sampler.output_stats()
        request: Request = Request(environ)
        if request.args.get("reset") in ("1", "true"):
            self.sampler.reset()
        response: Response = Response(stats)
        return response(environ, start_response)

    def run(self) -> None:
        server: BaseWSGIServer = BaseWSGIServer(
            self.host, self.port, self.handle_request, _QuietHandler
        )
        server.log = lambda *args, **kwargs: None
        logger.info("serving-profiles", port=self.port)
        server.serve_forever()


class _QuietHandler(WSGIRequestHandler):
    def log_request(self, *args, **kwargs) -> None:
        """Suppress request logging so as not to pollute application logs."""
        pass


def run_profiler(host="0.0.0.0", port=16384) -> None:
    s = Sampler()
    s.start()
    e = Emitter(s, host, port)
    # e.run()
    e.daemon = True
    e.start()

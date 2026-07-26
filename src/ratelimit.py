"""Client-side rate limiter for the Hugging Face public API.

Measured constraint (anonymous access, 2026-07-26, this machine):
  * 499 requests were served in 164.7 s before the endpoint began returning HTTP 429
  * the budget became available again after roughly 75 s of idling
  * repo-metadata calls and parquet range reads draw on the SAME budget -- verified by
    observing parquet reads fail with 429 while the metadata quota was exhausted

So the sustainable rate is about 500 requests per ~240 s. A sliding-window limiter encodes
that directly and is self-correcting. An AIMD controller was tried first and behaved badly:
a burst of 429s drove the interval to its ceiling and the 3%-per-40-successes recovery was
far too slow, stalling the harvester at under 20 reads per several minutes.

A 429 is still handled as a safety net -- honour Retry-After and shrink the window capacity
a notch -- so the limiter adapts downward if the server's real budget is tighter.
"""
import collections
import re
import threading
import time

# The server states the budget explicitly in its 429 body:
#   "0/500 requests remaining in current 300s window"
# An earlier setting of 460/240s (1.92 req/s) exceeded the true 500/300s (1.67 req/s) and
# slowly drained the budget until requests began failing. These are the server's own numbers,
# with headroom.
WINDOW = 300.0      # seconds
CAPACITY = 440      # requests per window


class Limiter:
    def __init__(self, window=WINDOW, capacity=CAPACITY):
        self.window = window
        self.capacity = capacity
        self._times = collections.deque()
        self._lk = threading.Lock()
        self._pause_until = 0.0
        self.n_ok = 0
        self.n_429 = 0

    def acquire(self, cost=1):
        while True:
            with self._lk:
                now = time.monotonic()
                while self._times and now - self._times[0] > self.window:
                    self._times.popleft()
                wait = max(0.0, self._pause_until - now)
                if wait <= 0 and len(self._times) + cost <= self.capacity:
                    for _ in range(cost):
                        self._times.append(now)
                    return
                if wait <= 0:
                    wait = max(0.05, self.window - (now - self._times[0]))
            time.sleep(min(wait, 30.0))

    def ok(self):
        with self._lk:
            self.n_ok += 1

    def hit_429(self, err=None):
        """Honour Retry-After; shrink window capacity so the limiter adapts downward."""
        wait = None
        if err is not None:
            m = re.search(r"[Rr]etry after (\d+)", str(err))
            if m:
                wait = int(m.group(1))
        with self._lk:
            self.n_429 += 1
            self.capacity = max(120, int(self.capacity * 0.9))
            w = wait if wait is not None else 60.0
            self._pause_until = max(self._pause_until, time.monotonic() + w)
        return w

    def stats(self):
        with self._lk:
            return (f"cap={self.capacity}/{self.window:.0f}s inflight={len(self._times)} "
                    f"ok={self.n_ok} 429={self.n_429}")


def is_429(e):
    s = str(e)
    return "429" in s or "Too Many Requests" in s or "rate limit" in s.lower()


LIMITER = Limiter()

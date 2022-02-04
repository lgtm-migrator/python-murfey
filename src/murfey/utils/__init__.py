from __future__ import annotations

from queue import Queue
from threading import Thread
from typing import Optional
from uuid import uuid4


class Processor:
    def __init__(self, name: Optional[str] = None):
        self._in: Queue = Queue()
        self._out: Queue = Queue()
        self._previous: Optional[Processor] = None
        self.thread: Optional[Thread] = None
        self.name = name or str(uuid4())[:8]

    def __rshift__(self, other: Processor):
        self.point_to(other)

    def point_to(self, other: Processor):
        if isinstance(other, Processor):
            other._in = self._out
            other._previous = self

    def process(
        self,
        in_thread: bool = False,
        thread_name: str = "",
        daemon: bool = False,
        **kwargs,
    ):
        if in_thread:
            self.thread = Thread(
                target=self._process,
                kwargs=kwargs,
                name=thread_name or self.name,
                daemon=daemon,
            )
            self.thread.start()
        else:
            self._process(**kwargs)

    def _process(self, **kwargs):
        pass

    def wait(self):
        if self.thread:
            self.thread.join()

    def origin(self):
        if self._previous:
            return self._previous.origin()
        return self

    def stop(self):
        raise NotImplementedError(f"Processor {self} has no stop method implemented")

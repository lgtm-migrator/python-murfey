from __future__ import annotations

from murfey.utils import Processor


class Drain(Processor):
    def _process(self, **kwargs):
        if self._previous and self._previous.thread:
            while self._previous.thread.is_alive():
                self._in.get()

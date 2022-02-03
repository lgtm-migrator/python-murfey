from __future__ import annotations

from rich.progress import Progress

from murfey.utils import Processor
from murfey.utils.rsync import RsyncPipe


class ProgressMonitor(Processor):
    def __init__(self, name: str = "progress_monitor"):
        super().__init__(name=name)

        # self.progress = Progress()

    def _process(self, **kwargs):
        if isinstance(self._previous, RsyncPipe) and self._previous.thread:
            with Progress() as progress:
                task = progress.add_task("[green]Transferring...")
                while self._previous.thread.is_alive():
                    next_file = self._in.get()
                    if next_file is None:
                        break
                    current_total = len(
                        [
                            f
                            for f in self._previous._previous.dir.glob("**/*")
                            if not f.is_dir()
                        ]
                    )
                    progress.update(task, total=current_total, advance=1)
                    self._out.put(next_file)

    def wait(self):
        self._in.put(None)
        super().wait()

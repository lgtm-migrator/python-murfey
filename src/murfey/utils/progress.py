from __future__ import annotations

from queue import Empty

from rich.progress import Progress
from rich.prompt import Confirm

from murfey.utils import Processor
from murfey.utils.rsync import RsyncPipe


class ProgressMonitor(Processor):
    def __init__(self, name: str = "progress_monitor"):
        super().__init__(name=name)
        self._total: int = 0
        self._finalised: bool = False

    def _process(self, **kwargs):
        if isinstance(self._previous, RsyncPipe) and self._previous.thread:
            with Progress() as progress:
                task = progress.add_task("[green]Transferring...")
                progress.update(
                    task, total=self._total, advance=self._total, visible=False
                )
                while self._previous.thread.is_alive():
                    try:
                        next_file = self._in.get(timeout=10)
                    except Empty:
                        print("progress queue was empty")
                        progress.update(task, visible=False)
                        break

                    if not next_file:
                        break
                    if hasattr(self.origin(), "_file_pattern"):
                        file_pattern = self.origin()._file_pattern
                    else:
                        file_pattern = "*"
                    current_total = len(
                        [
                            f
                            for f in self._previous._previous.dir.glob(
                                f"**/{file_pattern}"
                            )
                            if not f.is_dir()
                        ]
                    )
                    progress.update(task, total=current_total, advance=1, visible=True)
                    self._out.put(next_file)
            if not self._finalised:
                stop = Confirm.ask("Stop transfer?")
                if stop:
                    self.origin().stop()
                    self._finalised = True
                self._process(**kwargs)

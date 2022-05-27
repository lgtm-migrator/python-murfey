from __future__ import annotations

import logging
import queue
import threading
from pathlib import Path
from typing import Optional

from murfey.util import Observer

logger = logging.getLogger("murfey.client.analyser")


class Analyser(Observer):
    def __init__(self):
        super().__init__()
        self._experiment_type = ""
        self._acquisition_software = ""
        self._batch_store = {}

        self.queue = queue.Queue[Optional[Path]]()
        self.thread = threading.Thread(name="Analyser", target=self._analyse)
        self._stopping = False
        self._halt_thread = False

    def _find_context(self, file_path: Path):
        split_file_name = file_path.name.split("_")
        if split_file_name == "Position":
            self._experiment_type = "tomography"
            self._acquisition_software = "tomo5"

    def _analyse(self):
        while not self._halt_thread:
            transferred_file = self.queue.get()
            if not self._experiment_type or not self._acquisition_software:
                self._find_context(transferred_file)

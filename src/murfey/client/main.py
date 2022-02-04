from __future__ import annotations

import argparse
import os
import pathlib
from typing import Tuple

import requests
from rich.prompt import Prompt

from murfey.utils.drain import Drain
from murfey.utils.file_monitor import Monitor
from murfey.utils.progress import ProgressMonitor
from murfey.utils.rsync import RsyncPipe


def run():
    parser = argparse.ArgumentParser(description="Start the Murfey client")
    parser.add_argument("--visit", help="Name of visit", required=True)
    args = parser.parse_args()
    print("Visit name: ", args.visit)
    visit = Prompt.ask(
        "Which visit is this?", choices=[v["Visit name"] for v in get_all_visits()]
    )
    print(f"chose visit {visit}")
    dir_to_watch = Prompt.ask("Which directory should be watched?")
    pattern = Prompt.ask("Pattern for files to match", default="*.tiff")
    destination = Prompt.ask("Where should files be transferred to?")
    monitor = watch_directory(pathlib.Path(dir_to_watch), file_pattern=pattern)
    rsync = start_transfer(monitor, pathlib.Path(destination))
    progress, drain = start_progress(rsync)
    # while stop := Confirm.ask("Continue transfer?"):
    #    pass
    # stop_watching(monitor)
    # rsync.wait()
    progress.wait()


def get_all_visits():
    bl = os.getenv("BEAMLINE")
    if bl:
        path = "http://127.0.0.1:8000/visits/" + bl
    else:
        raise RuntimeError("No BEAMLINE environment variable was specified")
    # uvicorn default host and port, specified in uvicorn.run in server/main.py
    r = requests.get(path)
    return r.json()


def get_visit_info(visit_name: str):
    bl = os.getenv("BEAMLINE")
    if bl:
        path = "http://127.0.0.1:8000/visits/" + bl + "/" + visit_name
    else:
        raise RuntimeError("No BEAMLINE environment variable was specified")
    # uvicorn default host and port, specified in uvicorn.run in server/main.py
    r = requests.get(path)
    return r.json()


def watch_directory(directory: pathlib.Path, file_pattern: str = "*") -> Monitor:
    monitor = Monitor(directory, file_pattern=file_pattern)
    monitor.process(in_thread=True)
    return monitor


def stop_watching(monitor: Monitor):
    monitor.stop()
    monitor.wait()


def start_transfer(monitor: Monitor, destination: pathlib.Path) -> RsyncPipe:
    rp = RsyncPipe(destination)
    monitor >> rp
    rp.process(in_thread=True)
    return rp


def start_progress(rp: RsyncPipe) -> Tuple[ProgressMonitor, Drain]:
    pm = ProgressMonitor()
    rp >> pm
    pm.process(in_thread=True)
    drain = Drain()
    pm >> drain
    drain.process(in_thread=True, daemon=True)
    return pm, drain

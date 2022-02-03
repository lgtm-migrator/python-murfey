from __future__ import annotations

import argparse
import os
import pathlib

import requests

from murfey.utils.drain import Drain
from murfey.utils.file_monitor import Monitor
from murfey.utils.process import ProgressMonitor
from murfey.utils.rsync import RsyncPipe


def run():
    parser = argparse.ArgumentParser(description="Start the Murfey client")
    parser.add_argument("--visit", help="Name of visit", required=True)
    args = parser.parse_args()
    print("Visit name: ", args.visit)
    print(get_all_visits().text)
    print(get_visit_info(args.visit).text)


def get_all_visits():
    bl = os.getenv("BEAMLINE")
    if bl:
        path = "http://127.0.0.1:8000/visits/" + bl
    else:
        raise RuntimeError("No BEAMLINE environment variable was specified")
    # uvicorn default host and port, specified in uvicorn.run in server/main.py
    r = requests.get(path)
    return r


def get_visit_info(visit_name: str):
    bl = os.getenv("BEAMLINE")
    if bl:
        path = "http://127.0.0.1:8000/visits/" + bl + "/" + visit_name
    else:
        raise RuntimeError("No BEAMLINE environment variable was specified")
    # uvicorn default host and port, specified in uvicorn.run in server/main.py
    r = requests.get(path)
    return r


def watch_directory(directory: pathlib.Path) -> Monitor:
    monitor = Monitor(directory)
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


def start_progress(rp: RsyncPipe) -> ProgressMonitor:
    pm = ProgressMonitor()
    rp >> pm
    pm.process(in_thread=True)
    drain = Drain()
    pm >> drain
    drain.process(in_thread=True)
    return pm

from __future__ import annotations

import argparse
import os
import pathlib
from typing import List, Optional

import requests
from rich.panel import Panel
from rich.text import Text
from textual.app import App
from textual.reactive import Reactive
from textual.widget import Widget
from textual.widgets import (
    Button,
    ButtonPressed,
    DirectoryTree,
    FileClick,
    Footer,
    ScrollView,
)

from murfey.utils.file_monitor import Monitor
from murfey.utils.rsync import RsyncPipe


class HoverButton(Button):

    mouse_over = Reactive(False)

    def render(self) -> Button:
        return Button(
            self.name,
            style=("white on dark_blue" if self.mouse_over else "black on #baf2e9"),
        )

    def on_enter(self):
        self.mouse_over = True

    def on_leave(self):
        self.mouse_over = False


class Question(Widget):
    def render(self) -> Panel:
        return Panel(self.name)


class VisitSelector(App):

    watch_directory: Optional[pathlib.Path] = None
    status_history: List[str] = ["Starting:"]
    _monitoring: bool = False

    async def on_load(self, event):
        await self.bind("q", "quit")

    async def on_mount(self):
        current_visits = get_all_visits()
        buttons = (HoverButton(cv["Visit name"]) for cv in current_visits)
        self.status_view = ScrollView()
        await self.view.dock(Footer(), edge="bottom")
        await self.view.dock(self.status_view, edge="bottom", size=20)
        await self.view.dock(*buttons, edge="right", size=70)
        await self._display()

    async def handle_button_pressed(self, message: ButtonPressed):
        assert isinstance(message.sender, Button)
        await self.view.dock(
            ScrollView(
                DirectoryTree(f"/scratch/kif41228/{message.sender.name}", "Select")
            ),
            edge="left",
            size=30,
        )

    async def handle_tree_click(self, message: FileClick):
        if not self._monitoring:
            adjust = bool(self.watch_directory)
            self.watch_directory = pathlib.Path(message.node.data.path)
            if self.watch_directory.is_dir():
                if adjust:
                    self.status_history[
                        -1
                    ] = f"directory selected {self.watch_directory}: start monitor? [y/n]"
                else:
                    self.status_history.append(
                        f"directory selected {self.watch_directory}: start monitor? [y/n]"
                    )
                await self._display()
                await self.bind("y", "choose(True)")
                await self.bind("n", "choose(False)")
            else:
                self.status_history.append(f"{self.watch_directory} is not a directory")
                self.watch_directory = None
                await self._display()

    async def action_choose(self, choice: bool):
        if self.watch_directory is not None:
            if choice:
                self.status_history.append(
                    f"directory {self.watch_directory} confirmed: starting monitor"
                )
            else:
                self.status_history.append(f"directory {self.watch_directory} rejected")
                self.watch_directory = None
            await self._display()
            await self._rsync_display()

    async def _display(self):
        await self.status_view.update(
            Text("\n".join(self.status_history), style="green"), home=False
        )

    async def _rsync_display(self):
        if self.watch_directory:
            self._monitoring = True
            self.status_history.append(
                f"{len([f for f in self.watch_directory.glob('**/*') if f.is_file()])} files seen in {self.watch_directory}"
            )
            await self._display()


def run():
    parser = argparse.ArgumentParser(description="Start the Murfey client")
    parser.add_argument("--visit", help="Name of visit", required=True)
    args = parser.parse_args()
    print("Visit name: ", args.visit)
    # current_visits = get_all_visits()
    # print(current_visits.text)
    vs = VisitSelector()
    vs.run(title="Select visit", log="textual.log")
    print(get_visit_info(args.visit))


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

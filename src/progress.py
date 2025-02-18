import os
import time
from rich.live import Live
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn
from rich.layout import Layout
from rich.console import Console, Group
from rich.text import Text
from datetime import datetime

class ProgressManager:
    def __init__(self, total_colors, total_pixels, total_tasks):
        self.console = Console()
        self.layout = Layout()
        self.log_lines = []
        
        self.color_total_progress = Progress(
            SpinnerColumn(),
            TextColumn("[yellow]Colors"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TextColumn("[bold]{task.completed}/{task.total}"),
        )
        self.color_total_task = self.color_total_progress.add_task("", total=total_colors)
        
        self.pixel_total_progress = Progress(
            SpinnerColumn(),
            TextColumn("[magenta]Pixels"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TextColumn("[bold]{task.completed}/{task.total}"),
        )
        self.pixel_total_task = self.pixel_total_progress.add_task("", total=total_pixels)
        
        self.color_progress = Progress(
            SpinnerColumn(),
            TextColumn("[blue]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TextColumn("[bold]{task.completed}/{task.total}"),
        )
        
        self.task_progress = Progress(
            SpinnerColumn(),
            TextColumn("[cyan]Task"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TextColumn("[bold]{task.completed}/{task.total}"),
        )
        self.task_total = total_tasks
        self.task_completed = 0
        self.task_task = self.task_progress.add_task("", total=total_tasks)
        
        self.log_group = Group(*self.log_lines)
        self.file_info = Text("")
        
        progress_panel = Panel(
            Group(
                self.color_total_progress,
                self.pixel_total_progress,
                self.task_progress,
                Text(""),
                self.color_progress,
                Text(""),
                Text(""),
                self.file_info,
            ),
            title="Progress Monitor",
            border_style="bright_blue"
        )
        
        self.log_panel = Panel(
            self.log_group,
            title="Runtime Log",
            border_style="bright_green"
        )
        
        self.layout.split_row(
            Layout(progress_panel, ratio=1),
            Layout(self.log_panel, ratio=1)
        )
        
        self.live = Live(
            self.layout,
            refresh_per_second=10,
            vertical_overflow="visible"
        )
        
        self.color_task = None
        self.completed_pixels = 0

    def log(self, message, level="info"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        color_map = {
            "info": "white",
            "success": "green",
            "warning": "yellow",
            "error": "red"
        }
        text = Text.assemble(
            (f"[{timestamp}] ", "dim"),
            (message, color_map.get(level, "white"))
        )
        self.log_lines.append(text)
        if len(self.log_lines) > 15:
            self.log_lines.pop(0)
        self.log_group = Group(*self.log_lines)
        self.log_panel.renderable = self.log_group

    def advance_total(self, completed_pixels):
        self.color_total_progress.advance(self.color_total_task)
        new_pixels = completed_pixels - self.completed_pixels
        if new_pixels > 0:
            self.pixel_total_progress.advance(self.pixel_total_task, new_pixels)
            self.completed_pixels = completed_pixels

    def start(self):
        self.start_time = time.time()
        self.live.start()

    def stop(self):
        self.live.stop()

    def init_color_progress(self, total, description):
        self.color_task = self.color_progress.add_task(description, total=total)

    def update_color(self, advance=1):
        if self.color_task is not None:
            self.color_progress.update(self.color_task, advance=advance)

    def advance_task(self):
        self.task_completed += 1
        self.task_progress.update(self.task_task, advance=1, description=f"Task {self.task_completed}/{self.task_total}")

    def update_file_info(self, filepath, offset_x, offset_y, width, height):
        filename = os.path.basename(filepath)
        end_x = offset_x + width - 1
        end_y = offset_y + height - 1
        self.file_info.plain = (
            f"File: {filename}\n"
            f"Location: ({offset_x},{offset_y})->({end_x},{end_y})\n"
            f"Size: {width}x{height}"
        ) 
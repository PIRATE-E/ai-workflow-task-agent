import winsound
from rich.align import Align
from rich.panel import Panel
from rich.text import Text
from src.config import settings


def print_message(msg, sender="user"):
    console = settings.console
    if sender == "user":
        icon = "👤"
        style = "bold cyan"
        label = "[USER]"
    elif sender == "ai":
        icon = "🤖"
        style = "bold green"
        label = "[AI]"
    elif sender == "tool":
        icon = "🛠️"
        style = "bold yellow"
        label = "[TOOL]"
    else:
        icon = ""
        style = ""
        label = ""
    panel = Panel(
        Align.left(Text(f"{icon} {label} {msg}", style=style)),
        border_style=style,
        padding=(1, 2),
    )
    console.print(panel)
    if settings.ENABLE_SOUND_NOTIFICATIONS:
        winsound.Beep(7200, 200)  # Play a sound for new message
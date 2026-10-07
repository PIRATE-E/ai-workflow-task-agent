try:
    import winsound
except ImportError:
    winsound = None  # Not available on Linux/Mac

from rich.align import Align
from rich.panel import Panel

from coldwind.core.runtime.CoreContextRegistry import ContextRegistry

# MIGRATED: settings.console removed; console now sourced via ContextRegistry.get().get_console().
# Config values are accessed via: ContextRegistry.get().get_settings().<field>


def print_message(msg: str, sender="user"):
    # MIGRATED: settings.console → ContextRegistry.get().get_console()
    console = ContextRegistry.get().get_console()
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

    # Fix: Handle newlines properly by using Rich's built-in newline support
    # Instead of Text(), use a simple string which Rich handles newlines correctly
    formatted_message = f"{icon} {label} {msg.strip()}"

    panel = Panel(
        Align.left(formatted_message),
        border_style=style,
        padding=(1, 2),
    )
    console.print(panel)
    if ContextRegistry.get().get_settings().enable_sound_notifications and winsound:
        winsound.Beep(7200, 200)  # Play a sound for new message

try:
    import winsound
except ImportError:
    winsound = None  # Not available on Linux/Mac

from coldwind.core.runtime.CoreContextRegistry import ContextRegistry
from rich.align import Align
from rich.panel import Panel

# MIGRATED: settings.console removed; console now sourced via ContextRegistry.get().get_console().
# Config values are accessed via: ContextRegistry.get().get_settings().<field>


def print_message(msg: str, sender="user"):
    # MIGRATED: settings.console → ContextRegistry.get().get_console()
    console = ContextRegistry.get().get_console()
    if not console:
        raise RuntimeError("console is not defined to print messages !!")

        # -------------------------------------------------------------------------
        # System Messages: Node progress, slash commands, routing notifications
        # Print directly to console with Rich markup instead of wrapping in a panel!
        # -------------------------------------------------------------------------
    if sender == "system":
        clean = msg.strip()
        if clean.startswith("----Node is"):
            # Node execution marker (indented green)
            console.print(
                f"\t\t----[bold green]{clean.replace('----Node is ', 'Node is ')}[/bold green]"
            )
        elif clean.startswith("Slash command executed:"):
            console.print(
                f"[u][red]Slash command executed:[/u][/red] {clean.replace('Slash command executed: ', '')}"
            )
        elif clean.startswith("Slash command execution failed:") or clean.startswith(
            "Invalid slash command:"
        ):
            console.print(f"[u][red]{clean}[/u][/red]")
        elif clean.startswith("Message classified as:"):
            console.print(
                f"[u][red]Message classified as[/u][/red]: {clean.replace('Message classified as: ', '')}"
            )
        else:
            # General system notification
            console.print(f"[dim]{clean}[/dim]")
        return

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
